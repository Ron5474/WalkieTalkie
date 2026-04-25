# Running evaluation on Google Colab (after local setup works)

1. Upload this repo (or clone from GitHub) in Colab.
2. **Model endpoint**: set `OLLAMA_BASE_URL` to a reachable Ollama host.
   - Localhost (`127.0.0.1`) will not work from Colab unless tunneled.
   - If you run Ollama on your laptop, expose it safely (e.g., tunnel) and set `%env OLLAMA_BASE_URL=...`.
3. Install:

```python
!pip install -r backend/requirements.txt
```

4. Ensure required models exist on the Ollama host (example):

```bash
ollama pull phi3:mini
ollama pull llama3.1:8b
ollama pull llava:7b
ollama pull nomic-embed-text
```

5. Ingest Chroma once (optional if you upload `backend/chroma_db`):

```python
%cd backend
!python ingest_data.py
```

6. Run eval:

```python
!python ../evaluation/run_eval.py --tier both
```

Download `evaluation/results/*.jsonl` for your report. The same steps can be copied into a `.ipynb` when you are ready.
