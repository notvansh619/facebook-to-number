import os
import json
import re
import requests
import xml.etree.ElementTree as ET
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

# ---------------- CONFIG ----------------
VALID_KEYS = ["freewithShatirowner", "Shatirowner","NotVansh02"]

def check_key():
    key = request.args.get("key")
    if key != VALID_KEY:
        return False
    return True

# ---------------- AUTH TOKENS ----------------
def get_auth_token():
    auth_path = "auth.json"
    if not os.path.exists(auth_path):
        return None, None
    with open(auth_path, "r") as file:
        auth_data = json.load(file)
    e_auth = auth_data.get("e-auth")
    e_auth_c = auth_data.get("e-auth-c")
    return e_auth, e_auth_c

default_auth = get_auth_token()
if not default_auth[0] or not default_auth[1]:
    raise RuntimeError("Missing 'e-auth' or 'e-auth-c' in auth.json")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36",
    "accept": "*/*",
    "e-auth-v": "e1",
    "e-auth": default_auth[0],
    "e-auth-c": default_auth[1],
    "e-auth-k": "PgdtSBeR0MumR7fO",
    "accept-charset": "UTF-8",
    "content-type": "application/x-www-form-urlencoded; charset=utf-8",
    "Accept-Encoding": "gzip",
    "Host": "api.eyecon-app.com",
    "Connection": "Keep-Alive"
}

# ---------------- HELPERS ----------------
def extract_facebook_id_from_url(url):
    m = re.search(r'facebook\.com/(?:v[0-9.]+/)?(\d+)/picture', url)
    if m:
        return m.group(1)
    m2 = re.search(r'facebook\.com/(\d+)/', url)
    if m2:
        return m2.group(1)
    return None

def parse_name_info(response_text):
    try:
        root = ET.fromstring(response_text)
        names = [elem.text for elem in root.findall(".//name")]
        return names if names else None
    except Exception:
        return None

# ---------------- EYEcON ----------------
def get_share_url(): 
    return requests.get("https://api.eyecon-app.com/app/share", headers=headers).text

def get_updated_contacts_info_url(): 
    return requests.get("https://api.eyecon-app.com/app/getupdatedcontactsinfo.jsp?cv=vc_613_vn_4.2025.07.30.2109_a", headers=headers).text

def get_fresh_pics_json_url(): 
    return requests.get("https://api.eyecon-app.com/app/getfreshpicsjson.jsp?init=0&cv=vc_613_vn_4.2025.07.30.2109_a&trigger=init-resume2", headers=headers).text

def get_pic_url(number):
    url = f"https://api.eyecon-app.com/app/pic?cli={number}&is_callerid=true&size=big&type=0&src=DefaultDialer&cancelfresh=0&cv=vc_613_vn_4.2025.07.30.2109_a"
    resp = requests.get(url, headers=headers, allow_redirects=False)
    
    if resp.status_code == 302:
        location_url = resp.headers.get("Location")
        if location_url and "facebook.com" in location_url:
            fb_id = extract_facebook_id_from_url(location_url)
            if fb_id:
                return {"facebook": f"https://facebook.com/{fb_id}", "photo_url": f"/facebookpic/{fb_id}.jpg"}
        return {"photo_url": location_url}

    elif resp.status_code == 200:
        return {"photo_url": f"/static/{number}.jpg"}

    return {"photo_url": "Not available"}

def get_names_url(number):
    url = f"https://api.eyecon-app.com/app/getnames.jsp?cli={number}&lang=en&is_callerid=true&is_ic=true&cv=vc_613_vn_4.2025.07.30.2109_a"
    return requests.get(url, headers=headers).text

# ---------------- FLIPCARTSTORE ----------------
def flipcartstore_lookup(number):
    url = f"https://flipcartstore.serv00.net/api.php?phone={number}"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"error": "Flipcartstore API failed"}
    except Exception as e:
        return {"error": str(e)}

# ---------------- FLASK ROUTES ----------------
@app.route("/facebookpic/<facebook_id>.jpg", methods=["GET"])
def facebook_pic(facebook_id):
    fb_url = f"https://graph.facebook.com/{facebook_id}/picture?width=600&access_token=1716660955257637%7Cafa3f38c55f24c73b177afc962969b15"
    resp = requests.get(fb_url, stream=True)
    
    if resp.status_code == 200:
        return Response(resp.content, mimetype="image/jpeg")
    
    return jsonify({
        "developer": "@Shatirowner",
        "error": "Facebook image not found"
    }), 404

@app.route("/static/<number>.jpg", methods=["GET"])
def stream_image(number):
    resp = requests.get(
        f"https://api.eyecon-app.com/app/pic?cli={number}&is_callerid=true&size=big&type=0&src=DefaultDialer&cancelfresh=0&cv=vc_613_vn_4.2025.07.30.2109_a",
        headers=headers
    )
    
    if resp.status_code == 200:
        return Response(resp.content, mimetype="image/jpeg")
    
    return jsonify({
        "developer": "@Shatirowner",
        "error": "Image not available"
    }), 404

@app.route("/lookup", methods=["GET"])
def lookup():
    if not check_key():
        return jsonify({
            "developer": "@Shatirowner",
            "error": "Invalid key {YOU NEED KEY DM - @Shatirowner}"
        }), 403
        
    number = request.args.get("number")
    if not number:
        return jsonify({
            "developer": "@Shatirowner",
            "error": "Missing 'number' parameter"
        }), 400

    # Pre-call Eyecon APIs
    get_share_url()
    get_updated_contacts_info_url()
    get_fresh_pics_json_url()

    # Eyecon data
    name_info_raw = get_names_url(number)
    name_info = parse_name_info(name_info_raw)
    image_data = get_pic_url(number)

    # Flipcartstore data
    flip_data = flipcartstore_lookup(number)

    # Final JSON Output
    return jsonify({
        "developer": "@Shatirowner",
        "number": number,
        "name_info_raw": name_info_raw,
        "name_info": name_info,
        "photo_url": image_data.get("photo_url", "Not available"),
        "facebook": image_data.get("facebook"),
        "flipcartstore": flip_data
    })

# ---------------- MAIN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
