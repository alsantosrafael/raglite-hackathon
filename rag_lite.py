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
    
    return list(keywords)

def extract_sql_keywords(sql_query, method_name=None):
    """Extract keywords from SQL and method names"""
    keywords = set()
    
    # Table names
    tables = re.findall(r'(?:FROM|JOIN)\s+([a-zA-Z0-9_]+)', sql_query, re.IGNORECASE)
    keywords.update(tables)
    
    # Column names
    columns = re.findall(r'(?:SELECT|WHERE)\s+.*?([a-zA-Z0-9_]+)', sql_query, re.IGNORECASE)
    keywords.update(columns)
    
    # JPA method keywords
    if method_name:
        method_keywords = re.findall(r'[A-Z][a-z0-9]+', method_name)
        keywords.update([k.lower() for k in method_keywords])
    
    return keywords

def extract_content_keywords(content):
    """Extract entity/class names from content"""
    # Look for class names, table names, etc.
    entities = re.findall(r'(?:class|entity|table)\s+([A-Za-z0-9_]+)', content, re.IGNORECASE)
    return set(entities)

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
    relevant_snippets = []
    try:
        with open(kb_file, "r") as f:
            content = f.read()
            for keyword in keywords:
                # Find paragraphs containing the keyword
                for para in re.split(r'\n\s*\n', content):  # Split by paragraphs
                    if keyword.lower() in para.lower():
                        print(f"Matched keyword '{keyword}' in paragraph:\n{para[:100]}...")
                        relevant_snippets.append(para.strip())
                        if len(relevant_snippets) >= max_snippets:
                            return relevant_snippets
    except FileNotFoundError:
        print(f"Knowledge base file not found: {kb_file}")
        return []
    return relevant_snippets

def enrich_payload_with_rag(payload_json_path, max_context_tokens=10000):
    """Main function to enrich the payload with RAG context"""
    # Extract keywords from existing payload
    keywords = extract_keywords_from_payload(payload_json_path)
    print("Keywords for KB search:", keywords)
    
    # Search for relevant context within the payload
    relevant_context = search_payload_context(keywords, payload_json_path)
    
    # Search the knowledge base
    kb_snippets = search_knowledge_base(keywords)
    
    # Load and modify the payload
    with open(payload_json_path, 'r') as f:
        payload = json.load(f)
    
    # Add RAG context to the prompt
    if relevant_context or kb_snippets and 'messages' in payload:
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
                break
    
    # Write back the enriched payload
    with open(payload_json_path, 'w') as f:
        json.dump(payload, f, indent=2)
    
    return payload