from huggingface_hub import snapshot_download
print('Pre-downloading ESMFold model v1...')
snapshot_download('facebook/esmfold_v1', resume_download=True)
print('ESMFold model cached in image.')
