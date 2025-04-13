import boto3
from bs4 import BeautifulSoup
import json

# AWS Config
region = 'eu-north-1'  # or your region
bucket_name = 'my-web-crawl-data'  # replace with your bucket name
raw_prefix = 'raw/'
index_key = 'index/index.json'

# Initialize S3 client
s3 = boto3.client('s3', region_name=region)

# Step 1: List all HTML files under raw/
def list_html_files():
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=raw_prefix)
    files = []
    for obj in response.get('Contents', []):
        if obj['Key'].endswith('.html'):
            files.append(obj['Key'])
    return files

# Step 2: Download and extract text from HTML
def extract_text_from_s3_file(key):
    obj = s3.get_object(Bucket=bucket_name, Key=key)
    html = obj['Body'].read().decode('utf-8')
    soup = BeautifulSoup(html, 'html.parser')
    return soup.get_text()

# Step 3: Build the inverted index
def build_index(files):
    index = {}
    for file_key in files:
        try:
            text = extract_text_from_s3_file(file_key)
            tokens = text.lower().split()

            for word in tokens:
                word = word.strip().strip('.,!?()[]{}:;')  # basic cleaning
                if word:
                    if word not in index:
                        index[word] = []
                    if file_key not in index[word]:
                        index[word].append(file_key)
        except Exception as e:
            print(f"Error indexing {file_key}: {e}")
    return index

# Step 4: Upload the index back to S3
def upload_index_to_s3(index):
    index_json = json.dumps(index)
    s3.put_object(Bucket=bucket_name, Key=index_key, Body=index_json.encode('utf-8'))
    print(f"Index saved to s3://{bucket_name}/{index_key}")

# Main execution
if __name__ == '__main__':
    print("Indexer started...")
    html_files = list_html_files()
    print(f"Found {len(html_files)} HTML files to index.")
    inverted_index = build_index(html_files)
    upload_index_to_s3(inverted_index)
    print("Indexing completed.")
