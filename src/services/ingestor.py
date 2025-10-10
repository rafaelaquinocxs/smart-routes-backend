import json, os, time, logging
from datetime import datetime
from dotenv import load_dotenv
import paho.mqtt.client as mqtt
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime, timezone
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "cabrex/#")
MQTT_USERNAME = os.getenv("MQTT_USERNAME") or None
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD") or None
CLIENT_ID = os.getenv("CLIENT_ID", f"sr-ingestor-py-{int(time.time())}")
USE_TLS = os.getenv("USE_TLS", "false").lower() == "true"

API_URL = os.getenv("API_URL")
API_TOKEN = os.getenv("API_TOKEN")

# HTTP session com retry
session = requests.Session()
retry = Retry(
    total=5, backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["POST"]
)
session.mount("http://", HTTPAdapter(max_retries=retry))
session.mount("https://", HTTPAdapter(max_retries=retry))

def post_to_api(event: dict):
    headers = {"Content-Type": "application/json"}
    if API_TOKEN:
        headers["Authorization"] = f"Bearer {API_TOKEN}"
    try:
        r = session.post(API_URL, data=json.dumps(event), headers=headers, timeout=7)
        r.raise_for_status()
    except Exception as e:
        logging.error(f"Falha ao enviar para API: {e}")

def parse_topic(topic: str):
    # Ex.: cabrex/<deviceId>/status  -> {'root':'cabrex','deviceId':'<id>','metric':'status'}
    parts = topic.split("/")
    parsed = {"topic": topic}
    if len(parts) >= 1: parsed["root"] = parts[0]
    if len(parts) >= 2: parsed["deviceId"] = parts[1]
    if len(parts) >= 3: parsed["metric"] = "/".join(parts[2:])
    return parsed

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        logging.info("MQTT conectado")
        client.subscribe(MQTT_TOPIC, qos=0)
        logging.info(f"Assinado em {MQTT_TOPIC}")
    else:
        logging.error(f"Falha na conexão MQTT rc={rc}")

def on_message(client, userdata, msg: mqtt.MQTTMessage):
    payload_str = msg.payload.decode("utf-8", errors="replace").strip()
    data = payload_str
    try:
        data = json.loads(payload_str)
    except json.JSONDecodeError:
        pass  # mantém string bruta

    meta = parse_topic(msg.topic)
    event = {
        "topic": msg.topic,
        "meta": meta,
        "data": data,         # objeto (JSON) ou string
        "raw": payload_str,   # sempre mantém bruto
        "qos": msg.qos,
        "retain": msg.retain,
        "receivedAt": datetime.now(timezone.utc).isoformat()
    }
    if API_URL:
        post_to_api(event)
    else:
        logging.info(f"Recebido (sem API_URL): {event}")

def build_client():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=CLIENT_ID, clean_session=True)
    if MQTT_USERNAME and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    if USE_TLS:
        client.tls_set()  # use CA do sistema; para CA/cliente específicos, passar arquivos aqui
        if MQTT_PORT == 1883:
            logging.warning("USE_TLS=true mas porta 1883 — normalmente TLS usa 8883")

    client.will_set("cabrex/ingestor/status", payload="offline", qos=0, retain=True)
    client.on_connect = on_connect
    client.on_message = on_message
    return client

def main():
    client = build_client()
    while True:
        try:
            logging.info(f"Conectando em {MQTT_HOST}:{MQTT_PORT} …")
            client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            client.loop_forever(retry_first_connection=True)
        except Exception as e:
            logging.error(f"Erro MQTT (reconecta em 3s): {e}")
            time.sleep(3)

if __name__ == "__main__":
    main()
