import logging

import azure.functions as func
import azure.cognitiveservices.speech as speechsdk
from azure.cognitiveservices.language.luis.runtime import LUISRuntimeClient
from msrest.authentication import CognitiveServicesCredentials
import requests
import subprocess as sp
import os
import json

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    url = req.params.get('url')
    if not url:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            url = req_body.get('url')

    if url:
        sonuc = run(url)
        os.remove("outaudio.wav")
        return func.HttpResponse(body=json.dumps(sonuc),headers={"Content-type":"application/json"},status_code=200)
    else:
        sonuc = {"error":"url not found in payload"}
        return func.HttpResponse(body=json.dumps(sonuc),headers={"Content-type":"application/json"},status_code=400)

def run(url):
    download_convert(url)
    kisisel_asistan = asistan()
    sonuc = kisisel_asistan.sesli_komut_isle()
    return sonuc

def download_convert(url):
    output_filename="outaudio.wav"
    original_audio = requests.get(url)
    input_filename = url.split('/')[-1]
    with open(input_filename,'wb') as f:
        f.write(original_audio.content)
    bashCommand = f"ffmpeg -i {input_filename} {output_filename}"
    process = sp.Popen(bashCommand.split(),stdout=sp.PIPE)
    output,error = process.communicate()
    os.remove(input_filename)

class asistan():
    #Speech to text konfigurasyon
    speech_key, service_region = "<<Speech Key Buraya Gelecek>>", "<<Speech region Buraya Gelecek>>"
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region,speech_recognition_language="tr-TR")

    #LUIS konfigurasyon
    LUIS_RUNTIME_KEY="<<Luis Key Buraya Gelecek>>"
    LUIS_RUNTIME_ENDPOINT="<<Luis Endpoint Buraya Gelecek>>"
    LUIS_APP_ID="<<Luis App Id buraya gelecek>>"
    LUIS_APP_SLOT_NAME="<<Luis published model buraya gelecek. Secenekler: 'staging' ya da 'prodoction' >>"
    clientRuntime = LUISRuntimeClient(LUIS_RUNTIME_ENDPOINT, CognitiveServicesCredentials(LUIS_RUNTIME_KEY))

    def predict(self,query_text):
        request = { "query" : query_text }
        response = self.clientRuntime.prediction.get_slot_prediction(app_id=self.LUIS_APP_ID, slot_name=self.LUIS_APP_SLOT_NAME, prediction_request=request)

        return {"Amac": response.prediction.top_intent,"Ozellikler":response.prediction.entities}

    def sesli_komut_isle(self):
        #STT islemi
        audio_filename = "outaudio.wav"
        audio_input = speechsdk.audio.AudioConfig(filename=audio_filename)
        speech_recognizer = speechsdk.SpeechRecognizer(speech_config=self.speech_config, audio_config=audio_input)
        result = speech_recognizer.recognize_once()

        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            print("Ses tanimlandi: {}".format(result.text))
            #LUIS Islemi
            print("LUIS'e gonderiliyor")
            luisresult = self.predict(result.text)
            return luisresult
        elif result.reason == speechsdk.ResultReason.NoMatch:
            print("Ses tanimlanamadi: {}".format(result.no_match_details))
            return {}
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = result.cancellation_details
            print("Ses tanima iptal edildi: {}".format(cancellation_details.reason))
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                print("Hata detaylari: {}".format(cancellation_details.error_details))
            return {}