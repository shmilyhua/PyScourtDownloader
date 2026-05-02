import urllib.parse
import requests
import re
import os
import ctypes
import sys

HOST = "com3d2-shop-dl1.s-court.me"

def generate_target_url(local_url):
    parsed_url = urllib.parse.urlparse(local_url)
    segments = [s for s in parsed_url.path.split('/') if s]
    
    if segments and segments[0].lower() == "download":
        segments = segments[1:]
    
    params_dict = {}
    for i in range(0, len(segments) - 1, 2):
        key = segments[i]
        value = segments[i+1]
        params_dict[key] = value
            
    if "ver" not in params_dict:
        params_dict["ver"] = "2"
        
    params_dict["cmd"] = "11"
        
    ordered_params = {}
    if "itemid" in params_dict: ordered_params["itemid"] = params_dict["itemid"]
    if "ott" in params_dict: ordered_params["ott"] = params_dict["ott"]
    if "itoken" in params_dict: ordered_params["itoken"] = params_dict["itoken"]
    
    for k, v in params_dict.items():
        if k not in ordered_params:
            ordered_params[k] = v
            
    query_string = urllib.parse.urlencode(ordered_params)
    return f"http://{HOST}/api/download.php?{query_string}"

def download_bundle(target_url):
    print(f"\nContacting S-Court Servers...")
    headers = {"User-Agent": "COM3D2UP"}
    
    try:
        with requests.get(target_url, headers=headers, stream=True, timeout=300) as response:
            if response.status_code == 200:
                content_disposition = response.headers.get("Content-Disposition", "")
                filename_match = re.search(r'filename[^;=\n]*=(?:UTF-8\'\')?["\']?([^";\r\n\']+)["\']?', content_disposition, re.IGNORECASE)
                
                if not filename_match:
                    body = response.text.strip()
                    if body in ["-7", "-8"]:
                        print(f"Failed: Token expired or invalid auth (Error {body}).")
                        print("Generate a new link from the official client.")
                    else:
                        print(f"Failed: Server returned error code {body}")
                    return
                    
                raw_filename = filename_match.group(1)
                file_size = int(response.headers.get("Content-Length", 0))
                
                tmp = raw_filename
                if "!" not in tmp:
                    tmp = f"{tmp}.{file_size}!"
                elif not tmp.endswith("!"):
                    tmp = f"{tmp}!"
                    
                files = []
                while "!" in tmp:
                    exclamation_point = tmp.find("!")
                    dot_point = tmp.rfind(".", 0, exclamation_point)
                    
                    file_record_length = int(tmp[dot_point + 1:exclamation_point])
                    file_name_actual = tmp[:dot_point]
                    
                    files.append({
                        "name": file_name_actual,
                        "length": file_record_length,
                        "length_remaining": file_record_length,
                        "fd": open(file_name_actual, "wb")
                    })
                    tmp = tmp[exclamation_point + 1:]
                    
                print(f"Server packaged {len(files)} files for download.\n")
                total_bytes_read = 0
                
                for chunk in response.iter_content(chunk_size=81920):
                    if not chunk or not files:
                        continue
                        
                    bytes_read = len(chunk)
                    chunk_offset = 0
                    
                    while chunk_offset < bytes_read and files:
                        current_file = files[0]
                        length_to_modify = min(current_file["length_remaining"], bytes_read - chunk_offset)
                        
                        slice_data = chunk[chunk_offset:chunk_offset + length_to_modify]
                        current_file["fd"].write(slice_data)
                        
                        current_file["length_remaining"] -= length_to_modify
                        total_bytes_read += length_to_modify
                        chunk_offset += length_to_modify
                        
                        percent = (total_bytes_read / current_file["length"]) * 100 if current_file["length"] > 0 else 0
                        print(f"\rDownloading \"{current_file['name']}\" {total_bytes_read:,} / {current_file['length']:,} B ({percent:.0f}%)", end="")
                        
                        if current_file["length_remaining"] == 0:
                            current_file["fd"].close()
                            print(f"\nSuccessfully downloaded {current_file['name']}.")
                            files.pop(0)
                            if files:
                                total_bytes_read = 0
                                
                print("\nAll files retrieved successfully.")
                
            else:
                print(f"Failed to download. HTTP Status: {response.status_code}")
                
    except requests.exceptions.RequestException as e:
        print(f"Failed to download: {e}")

if __name__ == "__main__":
    if os.name == 'nt':
        ctypes.windll.kernel32.SetConsoleTitleW("S-Court Direct Downloader")
        
    print("S-Court Direct Downloader (Continuous Mode)")
    print("-" * 50)
    
    # Continuous execution loop
    while True:
        try:
            local_url = input("\nPaste localhost link (or type 'exit' to quit):\n> ").strip()
            
            if local_url.lower() in ['exit', 'quit']:
                print("Shutting down.")
                break
                
            if not local_url:
                continue
                
            target_url = generate_target_url(local_url)
            download_bundle(target_url)
            
        except KeyboardInterrupt:
            print("\nShutting down.")
            break
