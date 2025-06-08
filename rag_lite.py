import json
import re
import os

def extract_keywords_from_payload(payload_json_path):
    """Extract keywords from the existing payload.json"""
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
    
    # Add some general SQL optimization keywords
    keywords.update(['index', 'optimization', 'performance', 'query', 'sql'])
    
    print(f"🔍 Extracted keywords: {list(keywords)}")
    return list(keywords)

def extract_sql_keywords(sql_query, method_name=None):
    """Extract keywords from SQL and method names"""
    keywords = set()
    
    # Table names (melhorado)
    tables = re.findall(r'(?:FROM|JOIN|UPDATE|INTO)\s+([a-zA-Z0-9_]+)', sql_query, re.IGNORECASE)
    keywords.update(tables)
    
    # Column names (melhorado - pega múltiplas palavras)
    # Remove common SQL keywords first
    sql_clean = re.sub(r'\b(SELECT|FROM|WHERE|JOIN|ON|AND|OR|ORDER|BY|GROUP|HAVING|LIMIT)\b', '', sql_query, flags=re.IGNORECASE)
    columns = re.findall(r'\b([a-zA-Z0-9_]+)\b', sql_clean)
    keywords.update([col.lower() for col in columns if len(col) > 2])  # Ignore very short words
    
    # JPA method keywords
    if method_name:
        method_keywords = re.findall(r'[A-Z][a-z0-9]+', method_name)
        keywords.update([k.lower() for k in method_keywords])
    
    return keywords

def extract_content_keywords(content):
    """Extract entity/class names and general keywords from content"""
    keywords = set()
    
    # Look for class names, table names, etc.
    entities = re.findall(r'(?:class|entity|table)\s+([A-Za-z0-9_]+)', content, re.IGNORECASE)
    keywords.update(entities)
    
    # Extract general important words (melhorado)
    important_words = re.findall(r'\b(index|optimization|performance|query|sql|database|table|column|join|select|where)\b', content, re.IGNORECASE)
    keywords.update([word.lower() for word in important_words])
    
    return keywords

def search_payload_context(keywords, payload_json_path, max_snippets=3):
    """Search within the payload for relevant context"""
    with open(payload_json_path, 'r') as f:
        payload = json.load(f)
    
    relevant_snippets = []
    
    # Search in repository classes
    if 'repositories' in payload:
        for repo in payload['repositories']:
            repo_content = str(repo)
            relevance_score = 0
            for keyword in keywords:
                if keyword.lower() in repo_content.lower():
                    relevance_score += 1
            if relevance_score > 0:
                snippet = f"Repository: {repo.get('name', 'Unknown')}\n{repo_content[:300]}..."
                relevant_snippets.append((snippet, relevance_score))
    
    # Search in entity classes
    if 'entities' in payload:
        for entity in payload['entities']:
            entity_content = str(entity)
            relevance_score = 0
            for keyword in keywords:
                if keyword.lower() in entity_content.lower():
                    relevance_score += 1
            if relevance_score > 0:
                snippet = f"Entity: {entity.get('name', 'Unknown')}\n{entity_content[:300]}..."
                relevant_snippets.append((snippet, relevance_score))
    
    # Sort snippets by relevance score
    relevant_snippets.sort(key=lambda x: x[1], reverse=True)
    
    return [snippet for snippet, score in relevant_snippets[:max_snippets]]

def search_knowledge_base(keywords, kb_file="knowledgeBase/info.txt", max_snippets=2):
    """Search the knowledge base file for relevant snippets."""
    print(f"🔍 Searching KB with keywords: {keywords}")
    relevant_snippets = []
    try:
        with open(kb_file, "r") as f:
            content = f.read()
            print(f"📚 KB content length: {len(content)} chars")
            
            for keyword in keywords:
                # Find paragraphs containing the keyword
                for para in re.split(r'\n\s*\n', content):  # Split by paragraphs
                    if keyword.lower() in para.lower():
                        print(f"✅ Matched keyword '{keyword}' in paragraph:\n{para[:100]}...")
                        relevant_snippets.append(para.strip())
                        if len(relevant_snippets) >= max_snippets:
                            return relevant_snippets
    except FileNotFoundError:
        print(f"❌ Knowledge base file not found: {kb_file}")
        return []
    
    print(f"📚 Found {len(relevant_snippets)} KB snippets")
    return relevant_snippets

def enrich_payload_with_rag(payload_json_path, max_context_tokens=10000):
    """Main function to enrich the payload with RAG context"""
    # Extract keywords from existing payload
    keywords = extract_keywords_from_payload(payload_json_path)
    
    # Search for relevant context within the payload
    relevant_context = search_payload_context(keywords, payload_json_path)
    print(f"📝 Found {len(relevant_context)} payload context snippets")
    
    # Search the knowledge base
    kb_snippets = search_knowledge_base(keywords)
    
    # Load and modify the payload
    with open(payload_json_path, 'r') as f:
        payload = json.load(f)
    
    # CORREÇÃO: Parênteses corretos na condição
    if (relevant_context or kb_snippets) and 'messages' in payload:
        print("✅ Adding context to messages")
        context_parts = []
        if relevant_context:
            context_parts.append("Relevant code context from your codebase:\n" + "\n\n".join(relevant_context))
        if kb_snippets:
            context_parts.append("Knowledge base insights:\n" + "\n\n".join(kb_snippets))
        
        context_text = "\n\n".join(context_parts)
        
        # Truncate context text to fit within token limit
        if len(context_text) > max_context_tokens:
            context_text = context_text[:max_context_tokens]
        
        rag_addition = f"\n\n{context_text}\n"
        
        # Add to the last user message (assuming that's your main prompt)
        for message in reversed(payload['messages']):
            if message.get('role') == 'user':
                message['content'] += rag_addition
                print("✅ Context added to user message")
                break
    else:
        print(f"❌ No context to add. Context: {len(relevant_context)}, KB: {len(kb_snippets)}, Messages: {'messages' in payload}")
    
    # Write back the enriched payload
    with open(payload_json_path, 'w') as f:
        json.dump(payload, f, indent=2)
    
    return payload