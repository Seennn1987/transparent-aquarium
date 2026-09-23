"""起動中の Blender (MCP for Blender アドオン, port 9876) にコマンドを送る小道具。

使い方:
  python3 mcp_send.py code <pythonファイル>   # ファイルの中身を Blender 内で実行
  python3 mcp_send.py screenshot <保存先.png>  # 3Dビューのスクリーンショット
  python3 mcp_send.py info                     # シーン情報
"""
import json
import socket
import sys


def send(command, timeout=180):
    with socket.create_connection(("127.0.0.1", 9876), timeout=timeout) as s:
        s.sendall(json.dumps(command).encode("utf-8"))
        buf = b""
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
            try:
                return json.loads(buf.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
    raise RuntimeError("Blender から応答がありませんでした")


def main():
    mode = sys.argv[1]
    if mode == "code":
        with open(sys.argv[2], encoding="utf-8") as f:
            code = f.read()
        res = send({"type": "execute_code", "params": {"code": code}})
    elif mode == "screenshot":
        res = send({"type": "get_viewport_screenshot",
                    "params": {"filepath": sys.argv[2], "max_size": 1200}})
    elif mode == "info":
        res = send({"type": "get_scene_info", "params": {}})
    else:
        raise SystemExit(f"unknown mode: {mode}")

    if res.get("status") != "success":
        print(json.dumps(res, ensure_ascii=False, indent=2))
        raise SystemExit(1)
    result = res.get("result")
    if isinstance(result, dict) and "result" in result:
        print(result["result"])
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
