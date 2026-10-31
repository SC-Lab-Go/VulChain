1. We extrat the modelID using Hugging Face’s public Hub REST API: GET https://huggingface.co/api/models
2. Load the read token saved by hf auth login and create authenticated HTTP sessions.
3. We build an API filter for each relationship (FT, Adapter, Quantization, Merge), For instance, base_model:finetune:google-bert/bert-base-uncased, it sends the filter to https://huggingface.co/api/models.
4. Run one API filter for each relationship:
   base_model:finetune:<source-model>
   base_model:adapter:<source-model>
   base_model:quantized:<source-model>
   base_model:merge:<source-model>
5. Follow every API pagination link so results are not limited to the first page.
6. For every returned model object, extract the target repository ID:
   target = item.get("modelId") or item.get("id")
7. Construct graph edges in this direction:
   base/source model → derived/target model
   with the CSV schema:
   Source,Edge_type,Target
8. Mark a source model complete only after all four relationship queries succeed:
finetune → quantized → adapter → merge

====


nohup python -u graph_model_model_master.py \
  --input delta_model-2026-Aug28.csv \
  --output graph_model_model_first_200k.csv \
  --start 0 \
  --end 200000 \
  --workers 4 \
  --request-interval 0.5 \
  > graph_model_model_first_200k.nohup.log 2>&1 &

echo $!

tail -f graph_model_model_first_200k.nohup.log
ps -p <PID> -o pid,etime,%cpu,%mem,cmd

head graph_model_model_first_200k.csv

wc -l \
  graph_model_model_first_200k.csv \
  graph_model_model_first_200k.csv.completed.txt \
  graph_model_model_first_200k.csv.errors.csv


====

python3.10 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

hf auth login
<REDACTED>