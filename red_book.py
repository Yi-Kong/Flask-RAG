import json

import requests

from config import Config


def red_coze(content):
    url = "https://api.coze.cn/v1/workflow/run"
    workflow_id = Config.COZE_WORKFLOW_ID
    Secret_token = Config.COZE_API_TOKEN

    headers = {
        "Authorization": f"Bearer {Secret_token}",
        "Content-Type": "application/json"
    }

    payload ={
        "workflow_id": workflow_id,
        "parameters":{
            "lwq":content
        }
    }

    # 发送请求
    response = requests.post(url, headers=headers, json=payload)
    print(response.text)

    data = response.json()
    data1 = data.get("data")
    data2 = json.loads(data1)
    data3 = data2.get("output")
    print(data3)
    return data3


if __name__ == '__main__':
    red_coze("我喜欢玩LOL")