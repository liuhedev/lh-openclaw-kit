import sys
import os
import requests
from feishu_client import get_token

def download_image(message_id, file_key, output_path):
    token = get_token()
    url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/resources/{file_key}?type=image"
    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        stream=True,
        timeout=60
    )
    response.raise_for_status()
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"Successfully downloaded resource {file_key} from message {message_id} to {output_path}")

if __name__ == "__main__":
    download_image("om_x100b55e2f8e5fca4b497958891b2ff7", "img_v3_02vj_c2138711-fd71-49dc-a618-dd1e3434bb0g", "content/articles/2026-03-08/resources/images/01-scene-error-mockup.png")
