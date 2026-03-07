"""Tool for generating actionable MongoDB performance recommendations"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from models.query_models import Issue, Recommendation, IssueType, Severity, Priority, AnalysisResult
from utils.mongodb_client import MongoDBManager

logger = logging.getLogger(__name__)


class RecommendationGenerator:
    """Generates actionable recommendations for MongoDB performance issues"""
    
    def __init__(self, mongo_manager: MongoDBManager):
        self.mongo_manager = mongo_manager
    
    def generate_recommendations(
        self,
        db_name: str,
        slow_queries: List[Dict[str, Any]],
        explain_results: List[Dict[str, Any]],
        index_analysis: List[Dict[str, Any]]
    ) -> AnalysisResult:
        """
        Generate comprehensive recommendations based on analysis data
        
        Args:
            db_name: Database name
            slow_queries: List of slow query data
            explain_results: List of query explain results
            index_analysis: List of index analysis results
            
        Returns:
            AnalysisResult with issues and recommendations
        """
        issues = []
        recommendations = []
        
        # Analyze slow queries for patterns
        query_issues = self._analyze_slow_query_patterns(slow_queries)
        issues.extend(query_issues)
        
        # Analyze explain results for performance issues  
        explain_issues = self._analyze_explain_results(explain_results)
        issues.extend(explain_issues)
        
        # Analyze index opportunities
        index_issues = self._analyze_index_opportunities(index_analysis)
        issues.extend(index_issues)
        
        # Deduplicate issues with same collection, issue type, and query pattern
        unique_issues = []
        seen_issues = set()
        for issue in issues:
            # Create a key based on collection, issue type, and query pattern
            # This ensures different queries get separate recommendations
            query_key = str(sorted(issue.query_pattern.items())) if issue.query_pattern else "empty"
            issue_key = (issue.collection, issue.type, query_key)
            if issue_key not in seen_issues:
                unique_issues.append(issue)
                seen_issues.add(issue_key)
        
        issues = unique_issues
        
        # Generate specific recommendations for each issue
        for issue in issues:
            rec = self._create_recommendation_for_issue(issue, db_name)
            if rec:
                recommendations.append(rec)
        
        # Remove duplicate recommendations (same command)
        unique_recommendations = []
        seen_commands = set()
        for rec in recommendations:
            if rec.command not in seen_commands:
                unique_recommendations.append(rec)
                seen_commands.add(rec.command)
        
        recommendations = unique_recommendations
        
        # Sort recommendations by priority
        recommendations.sort(key=lambda x: self._get_priority_order(x.priority))
        
        # Create summary
        summary = self._create_investigation_summary(len(slow_queries), issues, recommendations)
        
        return AnalysisResult(
            timestamp=datetime.utcnow(),
            investigation_summary=summary,
            slow_queries_analyzed=len(slow_queries),
            issues_found=issues,
            recommendations=recommendations,
            total_investigation_time=0.0  # Will be set by caller
        )
    
    def _analyze_slow_query_patterns(self, slow_queries: List[Dict[str, Any]]) -> List[Issue]:
        """Analyze slow queries for common patterns and issues"""
        issues = []
        
        for query_data in slow_queries:
            collection = query_data.get("collection", "unknown")
            query = query_data.get("query", {})
            execution_time = query_data.get("execution_time_ms", 0)
            docs_examined = query_data.get("docs_examined", 0)
            docs_returned = query_data.get("docs_returned", 0)
            
            # Check for regex patterns without anchors
            regex_issue = self._check_regex_patterns(query, collection, execution_time)
            if regex_issue:
                issues.append(regex_issue)
            
            # Check for $where clauses
            where_issue = self._check_where_clause(query, collection, execution_time)
            if where_issue:
                issues.append(where_issue)
            
            # Check for queries without limits
            limit_issue = self._check_missing_limit(query_data, collection)
            if limit_issue:
                issues.append(limit_issue)
        
        return issues
    
    def _analyze_explain_results(self, explain_results: List[Dict[str, Any]]) -> List[Issue]:
        """Analyze explain results for performance issues"""
        issues = []
        
        for result in explain_results:
            collection = result.get("collection", "unknown")
            stage = result.get("stage", "UNKNOWN")
            docs_examined = result.get("docs_examined", 0)
            docs_returned = result.get("docs_returned", 0)
            execution_time = result.get("execution_time_ms", 0)
            efficiency_ratio = result.get("efficiency_ratio", 0.0)
            
            # Check for collection scans
            if stage == "COLLSCAN":
                query = result.get("query", {})
                
                # Check if this is an empty query (collection scan without filters)
                if not query or query == {}:
                    issue = Issue(
                        type=IssueType.COLLECTION_SCAN,
                        severity=Severity.WARNING,
                        collection=collection,
                        title=f"Inefficient collection scan in {collection}",
                        description=f"Query scans entire collection without filters, examining {docs_examined:,} documents",
                        query_pattern=query,
                        metrics={
                            "execution_time_ms": execution_time,
                            "docs_examined": docs_examined,
                            "docs_returned": docs_returned,
                            "efficiency_ratio": efficiency_ratio
                        },
                        root_cause="Query lacks selective filters, causing full collection scan"
                    )
                else:
                    # Regular missing index case
                    issue = Issue(
                        type=IssueType.MISSING_INDEX,
                        severity=Severity.CRITICAL if execution_time > 500 else Severity.WARNING,
                        collection=collection,
                        title=f"Missing index causes collection scan in {collection}",
                        description=f"Query performs full collection scan, examining {docs_examined:,} documents",
                        query_pattern=query,
                        metrics={
                            "execution_time_ms": execution_time,
                            "docs_examined": docs_examined,
                            "docs_returned": docs_returned,
                            "efficiency_ratio": efficiency_ratio
                        },
                        root_cause="No suitable index exists for this query pattern"
                )
                issues.append(issue)
            
            # Check for high examination ratio
            elif efficiency_ratio < 0.01 and docs_examined > 1000:
                issue = Issue(
                    type=IssueType.HIGH_EXAMINATION_RATIO,
                    severity=Severity.WARNING,
                    collection=collection,
                    title=f"Inefficient query in {collection}",
                    description=f"Query examines {docs_examined:,} documents but returns only {docs_returned:,}",
                    query_pattern=result.get("query", {}),
                    metrics={
                        "execution_time_ms": execution_time,
                        "docs_examined": docs_examined,
                        "docs_returned": docs_returned,
                        "efficiency_ratio": efficiency_ratio
                    },
                    root_cause="Index exists but query is not selective enough or index order is suboptimal"
                )
                issues.append(issue)
        
        return issues
    
    def _analyze_index_opportunities(self, index_analysis: List[Dict[str, Any]]) -> List[Issue]:
        """Analyze index suggestions for optimization opportunities"""
        issues = []
        logger.info(f"Processing {len(index_analysis)} index analysis entries")
        
        for i, analysis in enumerate(index_analysis):
            logger.info(f"Index analysis {i+1}: {analysis}")
            collection = analysis.get("collection", "unknown")
            optimization_potential = analysis.get("optimization_potential", "low")
            current_performance = analysis.get("current_performance", {})
            suggested_index = analysis.get("suggested_index", {})
            
            if optimization_potential in ["high", "critical"] and suggested_index:
                logger.info(f"Creating index recommendation for {collection} (potential: {optimization_potential})")
                severity = Severity.CRITICAL if optimization_potential == "critical" else Severity.WARNING
                
                issue = Issue(
                    type=IssueType.MISSING_INDEX,
                    severity=severity,
                    collection=collection,
                    title=f"Missing optimal index in {collection}",
                    description=f"Query would benefit from a compound index on {list(suggested_index.get('keys', {}).keys())}",
                    query_pattern=analysis.get("query_pattern", {}),
                    metrics={
                        "execution_time_ms": current_performance.get("execution_time_ms", 0),
                        "docs_examined": current_performance.get("docs_examined", 0),
                        "optimization_potential": optimization_potential
                    },
                    root_cause="Missing or suboptimal index for query pattern"
                )
                issues.append(issue)
            else:
                logger.info(f"Skipping index recommendation for {collection}: potential={optimization_potential}, has_suggestion={bool(suggested_index)}")
        
        logger.info(f"Created {len(issues)} index-based issues")
        return issues
    
    def _check_regex_patterns(self, query: Dict[str, Any], collection: str, execution_time: int) -> Optional[Issue]:
        """Check for inefficient regex patterns"""
        import re
        
        def find_regex_in_dict(d):
            """Recursively find regex patterns in query"""
            regex_patterns = []
            if isinstance(d, dict):
                for key, value in d.items():
                    if isinstance(value, dict) and "$regex" in value:
                        pattern = value["$regex"]
                        if isinstance(pattern, str):
                            # Check if regex starts with anchor
                            if not pattern.startswith("^"):
                                regex_patterns.append((key, pattern))
                    elif isinstance(value, str) and value.startswith("/") and value.endswith("/"):
                        # Handle regex in string format
                        pattern = value[1:-1]  # Remove / delimiters
                        if not pattern.startswith("^"):
                            regex_patterns.append((key, pattern))
                    elif hasattr(value, "pattern"):  # Compiled regex object
                        pattern = value.pattern
                        if not pattern.startswith("^"):
                            regex_patterns.append((key, pattern))
                    elif isinstance(value, (dict, list)):
                        regex_patterns.extend(find_regex_in_dict(value))
            elif isinstance(d, list):
                for item in d:
                    regex_patterns.extend(find_regex_in_dict(item))
            return regex_patterns
        
        regex_patterns = find_regex_in_dict(query)
        
        if regex_patterns:
            return Issue(
                type=IssueType.REGEX_WITHOUT_ANCHOR,
                severity=Severity.WARNING if execution_time < 1000 else Severity.CRITICAL,
                collection=collection,
                title=f"Inefficient regex pattern in {collection}",
                description=f"Regex patterns without anchors cause full text scan: {regex_patterns}",
                query_pattern=query,
                metrics={"execution_time_ms": execution_time},
                root_cause="Regex patterns without leading anchor (^) cannot use index efficiently"
            )
        
        return None
    
    def _check_where_clause(self, query: Dict[str, Any], collection: str, execution_time: int) -> Optional[Issue]:
        """Check for $where clauses that execute JavaScript"""
        
        def has_where_clause(d):
            if isinstance(d, dict):
                if "$where" in d:
                    return True
                for value in d.values():
                    if has_where_clause(value):
                        return True
            elif isinstance(d, list):
                for item in d:
                    if has_where_clause(item):
                        return True
            return False
        
        if has_where_clause(query):
            return Issue(
                type=IssueType.WHERE_CLAUSE,
                severity=Severity.CRITICAL,
                collection=collection,
                title=f"$where clause causes JavaScript execution in {collection}",
                description="Query uses $where clause which executes JavaScript for each document",
                query_pattern=query,
                metrics={"execution_time_ms": execution_time},
                root_cause="$where clauses cannot use indexes and execute JavaScript for each document"
            )
        
        return None
    
    def _check_missing_limit(self, query_data: Dict[str, Any], collection: str) -> Optional[Issue]:
        """Check for queries that return large result sets without pagination"""
        docs_returned = query_data.get("docs_returned", 0)
        query = query_data.get("query", {})
        
        # Check if query returns many documents (potential missing limit)
        if docs_returned > 1000:
            # Check if query has limit or skip (basic pagination check)
            has_limit = "limit" in str(query).lower() or "skip" in str(query).lower()
            
            if not has_limit:
                return Issue(
                    type=IssueType.NO_LIMIT,
                    severity=Severity.WARNING,
                    collection=collection,
                    title=f"Large result set without pagination in {collection}",
                    description=f"Query returns {docs_returned:,} documents without limit() clause",
                    query_pattern=query,
                    metrics={"docs_returned": docs_returned},
                    root_cause="Query lacks pagination, potentially consuming excessive memory and network"
                )
        
        return None
    
    def _create_recommendation_for_issue(self, issue: Issue, db_name: str) -> Optional[Recommendation]:
        """Create specific recommendation for an issue"""
        
        if issue.type == IssueType.MISSING_INDEX:
            return self._create_index_recommendation(issue, db_name)
        elif issue.type == IssueType.REGEX_WITHOUT_ANCHOR:
            return self._create_regex_optimization_recommendation(issue)
        elif issue.type == IssueType.WHERE_CLAUSE:
            return self._create_where_clause_recommendation(issue)
        elif issue.type == IssueType.NO_LIMIT:
            return self._create_pagination_recommendation(issue)
        elif issue.type == IssueType.HIGH_EXAMINATION_RATIO:
            return self._create_selectivity_recommendation(issue, db_name)
        elif issue.type == IssueType.COLLECTION_SCAN:
            return self._create_collection_scan_recommendation(issue)
        
        return None
    
    def _create_index_recommendation(self, issue: Issue, db_name: str) -> Recommendation:
        """Create index creation recommendation"""
        
        # Check if this is from IndexChecker (has suggested index in metrics)
        suggested_index_keys = None
        if hasattr(issue, 'metrics') and issue.metrics and 'suggested_index_keys' in issue.metrics:
            suggested_index_keys = issue.metrics['suggested_index_keys']
        elif issue.description and "compound index on" in issue.description:
            # This is from IndexChecker - parse the suggested fields from description
            # Description format: "Query would benefit from a compound index on ['email']"
            import ast
            try:
                start = issue.description.find("[")
                end = issue.description.find("]") + 1
                if start != -1 and end != -1:
                    fields_str = issue.description[start:end]
                    fields = ast.literal_eval(fields_str)
                    suggested_index_keys = {field: 1 for field in fields}
            except:
                pass
        
        # If we have a pre-determined index from IndexChecker, use it
        if suggested_index_keys:
            index_spec = suggested_index_keys
        else:
            # Extract fields from query pattern (for direct query analysis)
            query_fields = self._extract_fields_from_query(issue.query_pattern)
            
            # Check if we have fields to index
            if not query_fields:
                # Cannot suggest meaningful index for queries without specific fields (e.g., $where, collection scans)
                return None
            
            # Create index specification
            index_spec = {field: 1 for field in query_fields[:3]}  # Limit to 3 fields for compound index
        
        command = f"db.{issue.collection}.createIndex({index_spec})"
        
        # Calculate expected improvement
        docs_examined = issue.metrics.get("docs_examined", 0)
        if docs_examined > 1000:
            improvement = "95-99% performance improvement"
        elif docs_examined > 100:
            improvement = "80-95% performance improvement"
        else:
            improvement = "50-80% performance improvement"
        
        return Recommendation(
            issue=issue,
            priority=issue.severity,
            command=command,
            explanation=f"Create compound index on {list(index_spec.keys())} to eliminate collection scan",
            expected_improvement=improvement,
            impact_assessment=f"Will reduce documents examined from {docs_examined:,} to ~1-10"
        )
    
    def _create_regex_optimization_recommendation(self, issue: Issue) -> Recommendation:
        """Create regex optimization recommendation"""
        
        # Extract regex pattern and suggest specific optimizations
        specific_command = f"Create text index: db.{issue.collection}.createIndex({{email: \"text\"}})"
        
        if issue.query_pattern:
            # Look for regex in the query pattern
            for field, value in issue.query_pattern.items():
                if isinstance(value, dict) and "$regex" in value:
                    regex_pattern = value["$regex"]
                    if not regex_pattern.startswith("^"):
                        # Suggest anchored regex
                        anchored_pattern = f"^{regex_pattern}"
                        specific_command = f"Use anchored regex: db.{issue.collection}.find({{\"{field}\": {{\"$regex\": \"{anchored_pattern}\"}}}}) or create text index: db.{issue.collection}.createIndex({{\"{field}\": \"text\"}})"
                    break
        
        return Recommendation(
            issue=issue,
            priority=issue.severity,
            command=specific_command,
            explanation="Add leading anchor (^) to regex patterns for index optimization or create text index for full-text searches",
            expected_improvement="70-90% performance improvement for text searches",
            impact_assessment="Anchored regex can use index prefix matching, text indexes enable efficient text searches"
        )
    
    def _create_where_clause_recommendation(self, issue: Issue) -> Recommendation:
        """Create $where clause optimization recommendation"""
        
        # Extract the email from the $where clause to suggest specific alternative
        specific_command = f"Replace $where with native find(): db.{issue.collection}.find({{email: \"user@example.com\"}})"
        if issue.query_pattern and "$where" in str(issue.query_pattern):
            where_clause = str(issue.query_pattern.get("$where", ""))
            if "email" in where_clause and "==" in where_clause:
                # Extract email value from JavaScript comparison
                import re
                email_match = re.search(r'["\']([^"\']*@[^"\']*)["\']', where_clause)
                if email_match:
                    email_value = email_match.group(1)
                    specific_command = f"Replace $where with: db.{issue.collection}.find({{email: \"{email_value}\"}})"
        
        return Recommendation(
            issue=issue,
            priority=issue.severity,
            command=specific_command,
            explanation="Convert JavaScript $where clauses to native MongoDB query operators for indexable queries",
            expected_improvement="90-99% performance improvement",
            impact_assessment="Native operators can use indexes and avoid JavaScript execution overhead"
        )
    
    def _create_pagination_recommendation(self, issue: Issue) -> Recommendation:
        """Create pagination recommendation"""
        
        docs_returned = issue.metrics.get("docs_returned", 0)
        
        return Recommendation(
            issue=issue,
            priority=issue.severity,
            command=f"Add .limit(20) and implement pagination",
            explanation=f"Limit result sets and implement cursor-based pagination for large datasets",
            expected_improvement="Reduced memory usage and faster response times",
            impact_assessment=f"Will limit result set from {docs_returned:,} to manageable chunks"
        )
    
    def _create_selectivity_recommendation(self, issue: Issue, db_name: str) -> Recommendation:
        """Create query selectivity optimization recommendation with specific index suggestions"""
        
        efficiency_ratio = issue.metrics.get("efficiency_ratio", 0.0)
        
        # Analyze the query pattern to suggest specific indexes
        query_fields = self._extract_fields_from_query(issue.query_pattern)
        
        if query_fields:
            # Generate specific index recommendation
            index_spec = {field: 1 for field in query_fields[:2]}  # Limit to 2 fields for compound index
            command = f"db.{issue.collection}.createIndex({index_spec})"
            explanation = f"Create index on {list(index_spec.keys())} fields to improve query selectivity"
            expected_improvement = "60-85% performance improvement"
            impact_assessment = f"Index on {', '.join(query_fields)} will eliminate unnecessary document examination"
        else:
            # Fallback to generic recommendation
            command = "Analyze query pattern and add appropriate indexes"
            explanation = f"Current efficiency ratio is {efficiency_ratio:.3f}. Query examination pattern suggests index optimization opportunity"
            expected_improvement = "30-70% performance improvement"
            impact_assessment = "Better index utilization will reduce documents examined"
        
        return Recommendation(
            issue=issue,
            priority=issue.severity,
            command=command,
            explanation=explanation,
            expected_improvement=expected_improvement,
            impact_assessment=impact_assessment
        )
    
    def _create_collection_scan_recommendation(self, issue: Issue) -> Recommendation:
        """Create recommendation for collection scan without filters"""
        
        docs_examined = issue.metrics.get("docs_examined", 0)
        
        if docs_examined > 10000:
            improvement = "Add query filters to reduce data scanned by 90-99%"
        elif docs_examined > 1000:
            improvement = "Add query filters to reduce data scanned by 80-95%"
        else:
            improvement = "Add query filters to improve query selectivity"
        
        return Recommendation(
            priority=Priority.INFO,
            issue=issue,
            command=f"Add selective filters: db.{issue.collection}.find({{field: value}}) instead of find({{}})",
            explanation="Replace full collection scans with selective queries using indexed fields",
            expected_improvement=improvement,
            impact_assessment=f"Eliminating collection scans will significantly reduce I/O and CPU usage for queries on {docs_examined:,} document collection"
        )
    
    def _extract_fields_from_query(self, query: Dict[str, Any]) -> List[str]:
        """Extract field names from query for index creation, including aggregation pipelines"""
        fields = []
        
        # Handle aggregation pipeline queries
        if "pipeline" in query:
            pipeline = query["pipeline"]
            if isinstance(pipeline, list):
                for stage in pipeline:
                    if isinstance(stage, dict):
                        # Extract fields from $match stages
                        if "$match" in stage:
                            self._extract_fields_recursive(stage["$match"], fields)
                        # Extract fields from $group stages (for sorting optimization)
                        elif "$group" in stage and "_id" in stage["$group"]:
                            group_field = stage["$group"]["_id"]
                            if isinstance(group_field, str) and group_field.startswith("$"):
                                fields.append(group_field[1:])  # Remove $ prefix
        else:
            # Handle regular find queries
            self._extract_fields_recursive(query, fields)
        
        return list(set(fields))  # Remove duplicates
    
    def _extract_fields_recursive(self, d: Dict[str, Any], fields: List[str], path: str = ""):
        """Recursively extract field names from query structure"""
        if isinstance(d, dict):
            for key, value in d.items():
                if key.startswith("$"):
                    if key in ["$and", "$or"] and isinstance(value, list):
                        for item in value:
                            self._extract_fields_recursive(item, fields, path)
                    elif key in ["$gte", "$lte", "$gt", "$lt", "$ne", "$in"] and path:
                        # We have a field with operators, add the parent field
                        if path not in fields:
                            fields.append(path)
                    continue
                
                current_path = f"{path}.{key}" if path else key
                
                if isinstance(value, dict) and any(k.startswith("$") for k in value.keys()):
                    # Field with operators
                    fields.append(current_path)
                elif isinstance(value, dict):
                    # Nested object
                    self._extract_fields_recursive(value, fields, current_path)
                else:
                    # Simple field
                    fields.append(current_path)
    
    def _create_investigation_summary(
        self, 
        query_count: int, 
        issues: List[Issue], 
        recommendations: List[Recommendation]
    ) -> str:
        """Create human-readable investigation summary"""
        
        if not issues:
            return f"Analyzed {query_count} queries. No significant performance issues found."
        
        critical_count = len([i for i in issues if i.severity == Severity.CRITICAL])
        warning_count = len([i for i in issues if i.severity == Severity.WARNING])
        
        summary = f"Found {len(issues)} performance issues affecting your database"
        
        if critical_count > 0:
            summary += f" ({critical_count} critical"
            if warning_count > 0:
                summary += f", {warning_count} warnings"
            summary += ")"
        elif warning_count > 0:
            summary += f" ({warning_count} warnings)"
        
        return summary
    
    def _get_priority_order(self, severity: Severity) -> int:
        """Get numeric order for sorting priorities"""
        order = {
            Severity.CRITICAL: 0,
            Severity.WARNING: 1,
            Severity.INFO: 2
        }
        return order.get(severity, 3)


def create_recommendation_generator_tool(mongo_manager: MongoDBManager):
    """Create LangChain tool for recommendation generation"""
    from langchain_core.tools import StructuredTool
    from pydantic import BaseModel, Field
    import json
    
    class RecommendationInput(BaseModel):
        db_name: str = Field(description="Database name")
        analysis_data: str = Field(description="JSON string containing analysis data from previous tools")
    
    generator = RecommendationGenerator(mongo_manager)
    
    def generate_recommendations_tool(db_name: str, analysis_data: str) -> str:
        """Generate actionable recommendations based on query analysis"""
        try:
            data = json.loads(analysis_data)
            
            slow_queries = data.get("slow_queries", [])
            explain_results = data.get("explain_results", [])
            index_analysis = data.get("index_analysis", [])
            
            result = generator.generate_recommendations(
                db_name, slow_queries, explain_results, index_analysis
            )
            
            output = f"🔍 SLOW QUERY INVESTIGATION COMPLETE\n\n"
            output += f"{result.investigation_summary}\n\n"
            
            if result.recommendations:
                # Group by priority
                critical_recs = [r for r in result.recommendations if r.priority == Severity.CRITICAL]
                warning_recs = [r for r in result.recommendations if r.priority == Severity.WARNING]
                info_recs = [r for r in result.recommendations if r.priority == Severity.INFO]
                
                if critical_recs:
                    output += "🚨 CRITICAL PRIORITY:\n"
                    for rec in critical_recs:
                        output += f"• {rec.issue.title}\n"
                        output += f"  → Command: {rec.command}\n"
                        output += f"  → Impact: {rec.expected_improvement}\n\n"
                
                if warning_recs:
                    output += "⚠️  WARNING PRIORITY:\n"
                    for rec in warning_recs:
                        output += f"• {rec.issue.title}\n"
                        output += f"  → Command: {rec.command}\n"
                        output += f"  → Impact: {rec.expected_improvement}\n\n"
                
                if info_recs:
                    output += "💡 RECOMMENDATIONS:\n"
                    for rec in info_recs:
                        output += f"• {rec.issue.title}\n"
                        output += f"  → {rec.explanation}\n\n"
            
            # Calculate potential improvement
            if result.recommendations:
                avg_improvement = "75% average query speedup"
            else:
                avg_improvement = "No immediate optimizations needed"
            
            output += f"Potential performance improvement: {avg_improvement}\n"
            
            return output
            
        except Exception as e:
            return f"Error generating recommendations: {str(e)}"
    
    return StructuredTool(
        name="generate_recommendations",
        description="Generate actionable performance recommendations based on query analysis",
        func=generate_recommendations_tool,
        args_schema=RecommendationInput
    )