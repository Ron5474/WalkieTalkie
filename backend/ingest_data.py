import requests
from bs4 import BeautifulSoup
import chromadb
from langchain_community.embeddings import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os

URLS = [
    "https://49miles.com/2022/a-brief-history-of-san-francisco-everything-you-need-to-know/",
    "https://sfcityguides.org/tour/1840s-san-francisco-and-the-astonishing-legacy-of-americas-first-black-millionaire/",
    "https://sfcityguides.org/find-your-tour/"
]

def scrape_url(url):
    print(f"Scraping {url}...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        # Using BeautifulSoup pattern observed in the provided Jupyter Notebook
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove scripts and styles
        for script in soup(["script", "style", "nav", "footer"]):
            script.decompose()
            
        text = soup.get_text(separator=' ', strip=True)
        return text
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return ""

def main():
    print("Starting Vector DB ingestion...")
    
    documents = []
    for url in URLS:
        text = scrape_url(url)
        if text:
            documents.append({"text": text, "source": url})
            
    print("Splitting documents...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = []
    metadata = []
    
    for doc in documents:
        splits = text_splitter.split_text(doc["text"])
        chunks.extend(splits)
        metadata.extend([{"source": doc["source"]} for _ in splits])
        
    print(f"Created {len(chunks)} chunks.")
    
    # Initialize VectorDB
    # We will use local persistent ChromaDB and Ollama for embeddings
    db_path = os.path.join(os.path.dirname(__file__), "chroma_db")
    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_or_create_collection(name="local_stories")
    
    # We'll use nomic-embed-text for local embeddings
    # Please ensure you run: `ollama pull nomic-embed-text`
    embeddings_model = OllamaEmbeddings(model="nomic-embed-text", base_url="http://localhost:11434")
    
    print("Embedding and storing in ChromaDB. This may take a minute locally...")
    for i, chunk in enumerate(chunks):
        if i % 10 == 0:
            print(f"Processing chunk {i}/{len(chunks)}")
        try:
            emb = embeddings_model.embed_query(chunk)
            collection.add(
                embeddings=[emb],
                documents=[chunk],
                metadatas=[metadata[i]],
                ids=[f"doc_chunk_{i}"]
            )
        except Exception as e:
            print(f"Failed to embed chunk {i}: {e}")

    print(f"Ingestion complete. {len(chunks)} embedded and stored in {db_path}.")

if __name__ == "__main__":
    main()
