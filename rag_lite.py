import json
import re

def normalize_keywords(keywords):
    """Normalize keywords by removing stopwords, short words, and duplicates"""
    stop_words = {
        'the', 'a', 'an', 'in', 'on', 'of', 'is', 'are', 'and', 'or', 'to', 'from', 
        'for', 'with', 'by', 'at', 'as', 'be', 'this', 'that', 'it', 'if', 'not',
        'but', 'can', 'get', 'set', 'new', 'old', 'all', 'any', 'has', 'had'
    }
    
    normalized = set()
    for keyword in keywords:
        keyword = str(keyword).lower().strip()
        # Remove short words, stopwords, and purely numeric values
        if len(keyword) > 2 and keyword not in stop_words and not keyword.isdigit():
            normalized.add(keyword)
    
    return list(normalized)

def extract_keywords_from_payload(payload_json_path):
    """Extract keywords from the existing payload.json with improved extraction"""
    with open(payload_json_path, 'r') as f:
        payload = json.load(f)
    
    keywords = set()
    
    # Extract from SQL queries in the payload
    if 'queries' in payload:
        for query in payload['queries']:
            sql = query.get('sql', '')
            method = query.get('method_name', '')
            keywords.update(extract_sql_keywords(sql, method))
    
    # Extract from any messages/prompts in payload
    if 'messages' in payload:
        for message in payload['messages']:
            content = message.get('content', '')
            keywords.update(extract_content_keywords(content))
    
    # Extract from repositories
    if 'repositories' in payload:
        for repo in payload['repositories']:
            repo_content = str(repo)
            keywords.update(extract_java_keywords(repo_content))
    
    # Extract from entities
    if 'entities' in payload:
        for entity in payload['entities']:
            entity_content = str(entity)
            keywords.update(extract_java_keywords(entity_content))
    
    # Add some general optimization keywords
    keywords.update(['index', 'optimization', 'performance', 'query', 'sql', 'jpa', 'hibernate'])
    
    # Normalize all keywords
    normalized_keywords = normalize_keywords(keywords)
    
    print(f"🔍 Extracted {len(normalized_keywords)} normalized keywords: {normalized_keywords[:10]}...")
    return normalized_keywords

def extract_sql_keywords(sql_query, method_name=None):
    """Enhanced SQL keyword extraction"""
    keywords = set()
    
    if not sql_query:
        return keywords
    
    # Table names (improved pattern)
    tables = re.findall(r'(?:FROM|JOIN|UPDATE|INTO|TABLE)\s+([a-zA-Z0-9_]+)', sql_query, re.IGNORECASE)
    keywords.update(tables)
    
    # Column names (improved - remove SQL keywords first)
    sql_clean = re.sub(r'\b(SELECT|FROM|WHERE|JOIN|ON|AND|OR|ORDER|BY|GROUP|HAVING|LIMIT|DISTINCT|COUNT|SUM|AVG|MAX|MIN)\b', '', sql_query, flags=re.IGNORECASE)
    columns = re.findall(r'\b([a-zA-Z][a-zA-Z0-9_]*)', sql_clean)
    keywords.update([col.lower() for col in columns if len(col) > 2])
    
    # SQL operation keywords
    sql_operations = re.findall(r'\b(CREATE|ALTER|DROP|INDEX|CONSTRAINT|PRIMARY|FOREIGN|KEY|BATCH|CACHE|FETCH|LAZY|EAGER)\b', sql_query, re.IGNORECASE)
    keywords.update([k.lower() for k in sql_operations])
    
    # JPA method keywords (improved camelCase splitting)
    if method_name:
        # Split camelCase and PascalCase
        method_parts = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)', method_name)
        keywords.update([part.lower() for part in method_parts if len(part) > 2])
        
        # Also extract whole method name
        keywords.add(method_name.lower())
    
    return keywords

def extract_java_keywords(content):
    """Extract Java/Kotlin specific keywords from code content"""
    keywords = set()
    
    if not content:
        return keywords
    
    content_str = str(content)
    
    # Class names (improved pattern)
    class_names = re.findall(r'(?:class|interface|enum)\s+([A-Za-z][A-Za-z0-9_]*)', content_str, re.IGNORECASE)
    keywords.update([name.lower() for name in class_names])
    
    # Annotations (JPA, Spring, etc.)
    annotations = re.findall(r'@([A-Za-z][A-Za-z0-9_]*)', content_str)
    keywords.update([ann.lower() for ann in annotations])
    
    # Method names (camelCase splitting)
    methods = re.findall(r'(?:public|private|protected)?\s*\w+\s+([a-z][A-Za-z0-9_]*)\s*\(', content_str)
    for method in methods:
        method_parts = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)', method)
        keywords.update([part.lower() for part in method_parts if len(part) > 2])
    
    # Field/variable names
    fields = re.findall(r'(?:private|public|protected)\s+\w+\s+([a-zA-Z][a-zA-Z0-9_]*)', content_str)
    keywords.update([field.lower() for field in fields])
    
    # Package names
    packages = re.findall(r'package\s+([a-zA-Z][a-zA-Z0-9_.]*)', content_str)
    for package in packages:
        package_parts = package.split('.')
        keywords.update([part.lower() for part in package_parts if len(part) > 2])
    
    return keywords

def extract_content_keywords(content):
    """Enhanced content keyword extraction"""
    keywords = set()
    
    if not content:
        return keywords
    
    # Java/Kotlin keywords
    keywords.update(extract_java_keywords(content))
    
    # Database and JPA related terms
    db_terms = re.findall(r'\b(entity|repository|service|controller|table|column|join|select|where|index|optimization|performance|query|sql|database|hibernate|jpa|spring|batch|cache|fetch|lazy|eager)\b', content, re.IGNORECASE)
    keywords.update([term.lower() for term in db_terms])
    
    # Technical terms (camelCase aware)
    tech_terms = re.findall(r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)*|[a-z]+(?:[A-Z][a-z]+)+)\b', content)
    for term in tech_terms:
        # Split camelCase
        parts = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)', term)
        keywords.update([part.lower() for part in parts if len(part) > 2])
    
    return keywords

def calculate_relevance_score(text, keywords):
    """Calculate relevance score based on keyword matches"""
    if not text or not keywords:
        return 0
    
    text_lower = text.lower()
    score = 0
    matched_keywords = set()
    
    for keyword in keywords:
        keyword_lower = keyword.lower()
        count = text_lower.count(keyword_lower)
        if count > 0:
            # Weight by keyword length and frequency
            keyword_score = count * (len(keyword) / 5)  # Longer keywords get more weight
            score += keyword_score
            matched_keywords.add(keyword)
    
    # Bonus for multiple unique keywords matched
    if len(matched_keywords) > 1:
        score *= (1 + len(matched_keywords) * 0.1)
    
    return score

def search_payload_context(keywords, payload_json_path, max_snippets=3):
    """Enhanced payload context search with better scoring"""
    with open(payload_json_path, 'r') as f:
        payload = json.load(f)
    
    relevant_snippets = []
    
    # Search in repository classes
    if 'repositories' in payload:
        for repo in payload['repositories']:
            repo_content = str(repo)
            relevance_score = calculate_relevance_score(repo_content, keywords)
            if relevance_score > 0:
                snippet = f"Repository: {repo.get('name', 'Unknown')}\n{repo_content[:400]}..."
                relevant_snippets.append((snippet, relevance_score))
    
    # Search in entity classes
    if 'entities' in payload:
        for entity in payload['entities']:
            entity_content = str(entity)
            relevance_score = calculate_relevance_score(entity_content, keywords)
            if relevance_score > 0:
                snippet = f"Entity: {entity.get('name', 'Unknown')}\n{entity_content[:400]}..."
                relevant_snippets.append((snippet, relevance_score))
    
    # Search in queries
    if 'queries' in payload:
        for query in payload['queries']:
            query_content = f"SQL: {query.get('sql', '')} Method: {query.get('method_name', '')}"
            relevance_score = calculate_relevance_score(query_content, keywords)
            if relevance_score > 0:
                snippet = f"Query: {query.get('method_name', 'Unknown')}\n{query_content}"
                relevant_snippets.append((snippet, relevance_score))
    
    # Sort snippets by relevance score (highest first)
    relevant_snippets.sort(key=lambda x: x[1], reverse=True)
    
    print(f"📊 Payload context scores: {[(score, snippet[:50]) for snippet, score in relevant_snippets[:3]]}")
    
    return [snippet for snippet, score in relevant_snippets[:max_snippets]]

def chunk_knowledge_base(content, chunk_size=300, overlap=50):
    """Split knowledge base into overlapping chunks for better retrieval"""
    if not content:
        return []
    
    # Split by paragraphs first
    paragraphs = re.split(r'\n\s*\n', content)
    chunks = []
    
    for para in paragraphs:
        if len(para.strip()) < 50:  # Skip very short paragraphs
            continue
            
        words = para.split()
        if len(words) <= chunk_size:
            chunks.append(para.strip())
        else:
            # Split long paragraphs into overlapping chunks
            for i in range(0, len(words), chunk_size - overlap):
                chunk_words = words[i:i + chunk_size]
                chunk = ' '.join(chunk_words)
                chunks.append(chunk.strip())
    
    return chunks

# Global variable to cache knowledge base
_kb_chunks = None

def load_and_chunk_knowledge_base(kb_file="knowledgeBase/info.txt"):
    """Load and chunk knowledge base once, then cache it"""
    global _kb_chunks
    if _kb_chunks is None:
        try:
            with open(kb_file, "r") as f:
                content = f.read()
                _kb_chunks = chunk_knowledge_base(content)
                print(f"📚 Loaded and chunked KB into {len(_kb_chunks)} chunks")
        except FileNotFoundError:
            print(f"❌ Knowledge base file not found: {kb_file}")
            _kb_chunks = []
    return _kb_chunks

def search_knowledge_base(keywords, kb_file="knowledgeBase/info.txt", max_snippets=3):
    """Enhanced knowledge base search with chunking and scoring"""
    print(f"🔍 Searching KB with {len(keywords)} keywords: {keywords[:5]}...")
    
    chunks = load_and_chunk_knowledge_base(kb_file)
    if not chunks:
        return []
    
    scored_chunks = []
    
    for chunk in chunks:
        relevance_score = calculate_relevance_score(chunk, keywords)
        if relevance_score > 0:
            scored_chunks.append((chunk, relevance_score))
    
    # Sort by relevance score (highest first)
    scored_chunks.sort(key=lambda x: x[1], reverse=True)
    
    print(f"📊 KB search found {len(scored_chunks)} relevant chunks")
    if scored_chunks:
        print(f"📊 Top KB scores: {[score for chunk, score in scored_chunks[:3]]}")
    
    return [chunk for chunk, score in scored_chunks[:max_snippets]]

def format_context_for_injection(relevant_context, kb_snippets):
    """Format the context nicely for injection into the prompt"""
    context_parts = []
    
    if relevant_context:
        context_parts.append("=== RELEVANT CODE CONTEXT ===")
        for i, context in enumerate(relevant_context, 1):
            context_parts.append(f"Context {i}:")
            context_parts.append(context)
            context_parts.append("")
    
    if kb_snippets:
        context_parts.append("=== OPTIMIZATION KNOWLEDGE BASE ===")
        for i, snippet in enumerate(kb_snippets, 1):
            context_parts.append(f"Knowledge {i}:")
            context_parts.append(snippet)
            context_parts.append("")
    
    return "\n".join(context_parts)

def enrich_payload_with_rag(payload_json_path, max_context_tokens=30000):
    """Enhanced main function to enrich the payload with RAG context"""
    print("🚀 Starting RAG enrichment...")
    
    # Extract and normalize keywords from existing payload
    keywords = extract_keywords_from_payload(payload_json_path)
    
    if not keywords:
        print("❌ No keywords extracted, skipping RAG enrichment")
        return
    
    # Search for relevant context within the payload
    relevant_context = search_payload_context(keywords, payload_json_path, max_snippets=4)
    print(f"📝 Found {len(relevant_context)} payload context snippets")
    
    # Search the knowledge base
    kb_snippets = search_knowledge_base(keywords, max_snippets=3)
    print(f"📚 Found {len(kb_snippets)} KB snippets")
    
    # Load and modify the payload
    with open(payload_json_path, 'r') as f:
        payload = json.load(f)
    
    # Add context if we found any and there are messages to enrich
    if (relevant_context or kb_snippets) and 'messages' in payload:
        print("✅ Adding context to messages")
        
        # Format context nicely
        context_text = format_context_for_injection(relevant_context, kb_snippets)
        
        # Truncate context text to fit within token limit (rough estimation: 4 chars per token)
        max_context_chars = max_context_tokens * 4
        if len(context_text) > max_context_chars:
            context_text = context_text[:max_context_chars] + "\n\n[Context truncated due to token limit]"
            print(f"⚠️ Context truncated to fit {max_context_tokens} token limit")
        
        rag_addition = f"\n\n{context_text}\n\nBased on the above context, please provide your analysis and recommendations.\n"
        
        # Add to the last user message (assuming that's your main prompt)
        for message in reversed(payload['messages']):
            if message.get('role') == 'user':
                message['content'] += rag_addition
                print(f"✅ Added {len(context_text)} chars of context to user message")
                break
    else:
        print(f"❌ No context to add. Context: {len(relevant_context)}, KB: {len(kb_snippets)}, Messages: {'messages' in payload}")
    
    # Write back the enriched payload
    with open(payload_json_path, 'w') as f:
        json.dump(payload, f, indent=2)
    
    print("🎉 RAG enrichment completed!")
    return payload
