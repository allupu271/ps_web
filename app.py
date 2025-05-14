from flask import Flask, render_template, request, jsonify,redirect, url_for, session,flash
from azure.eventhub import EventHubConsumerClient
from azure.iot.hub import IoTHubRegistryManager
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import threading
import time
import json


app = Flask(__name__)
received_temperature = None
received_water = None

EVENT_HUB_CONNECTION_STRING = "Endpoint=sb://ihsuprodamres021dednamespace.servicebus.windows.net/;SharedAccessKeyName=iothubowner;SharedAccessKey=Iw9q0uxY/2pl3hNDcnUV3BjfByI6dYxOlAIoTNhQ/gs=;EntityPath=iothub-ehub-orice-63742525-28e3c9a222"
EVENT_HUB_NAME = "iothub-ehub-orice-63742525-28e3c9a222"  
CONSUMER_GROUP = "$Default" 


def send_email(subiect,mesaj):
    SMTP_SERVER = 'smtp.mail.yahoo.com'
    SMTP_PORT = 587
    SMTP_USERNAME = 'cmorar100@yahoo.ro'
    SMTP_PASSWORD = 'bqsxrsfiecsrjpik'
    RECIPIENT_EMAIL = 'lupualexandra308@gmail.com'

    message = MIMEMultipart()
    message['From'] = SMTP_USERNAME
    message['To'] = RECIPIENT_EMAIL
    message['Subject'] = subiect

    body = mesaj + time.strftime("%Y-%m-%d %H:%M:%S")
    message.attach(MIMEText(body, 'plain'))

    try:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            text = message.as_string()
            server.sendmail(SMTP_USERNAME, RECIPIENT_EMAIL, text)
            server.quit()
            print("E-mail trimis cu succes!")
    except Exception as e:
            print("Eroare la trimiterea e-mailului:", e)


def on_event(partition_context, event):
    try:
        message_body = json.loads(event.body_as_str())
        if("Potentiometer" in message_body):
            global received_temperature
            received_temperature = message_body["Potentiometer"]
            print(f"📩 New Message Received Temperatura: {message_body["Potentiometer"]}")
        if("WaterLevel" in message_body):
            global received_water
            received_water = message_body["WaterLevel"]
            print(f"📩 New Message Received Inundatie: {message_body["WaterLevel"]}")
            if(received_water >50):
                subiect = "Alerta inundatie!"
                mesaj = "A fost detectată o inundație la data și ora:"
                send_email(subiect, mesaj)
            
    except json.JSONDecodeError:
        print("❌ Failed to decode message body.")
    partition_context.update_checkpoint()  

def threaded_event_listener():
    try:
            print("🔌 Starting Event Hub listener...")
            client = EventHubConsumerClient.from_connection_string(EVENT_HUB_CONNECTION_STRING, consumer_group=CONSUMER_GROUP)
            with client:
                client.receive(on_event, starting_position="@latest")  # Read latest messages
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping Event Hub listener...")
    finally:
        client.close()

listener_thread = threading.Thread(target=threaded_event_listener, daemon=True)
listener_thread.start()

# Azure IoT Hub connection string and device ID
CONNECTION_STRING = "HostName=orice.azure-devices.net;SharedAccessKeyName=iothubowner;SharedAccessKey=Iw9q0uxY/2pl3hNDcnUV3BjfByI6dYxOlAIoTNhQ/gs="
DEVICE_ID = "ESP32"  
iot_hub_manager = IoTHubRegistryManager(CONNECTION_STRING)



@app.route('/')
def index():
    return render_template('a.html', temperatura=received_temperature, inundatie=received_water)


@app.route("/send_led_state", methods=["POST"])
def send_command():
    try:
        data = request.get_json()
        command = data["command"].lower()
        message = command
        print(f"📩 Sending command: {message}")
        iot_hub_manager.send_c2d_message(DEVICE_ID, message)
    except Exception as e:
        print(f"❌ Failed to send command: {e}")

    return jsonify({"status": "success", "message": "command"}), 200

if __name__ == '__main__':
    app.run(debug=True)