## seekorsurvey - Call seeking, automated surveying on failure
## 
## Written in 2015 by Vitorio Miliano <http://vitor.io/>
## 
## To the extent possible under law, the author has dedicated all copyright and related and neighboring rights to this software to the public domain worldwide.  This software is distributed without any warranty.
## 
## You should have received a copy of the CC0 Public Domain Dedication along with this software.  If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

from flask import Flask, request, redirect
import twilio.twiml
import twilio.rest
import ConfigParser
import mandrill
import requests

config = ConfigParser.ConfigParser()
config.readfp(open('seekorsurvey.cfg'))
twilio_number = config.get('seekorsurvey', 'twilio_number')
researcher_numbers = config.get('seekorsurvey', 'researcher_numbers').split(',')
researcher_voicemail_timeout = config.get('seekorsurvey', 'researcher_voicemail_timeout')
researcher_email = config.get('seekorsurvey', 'researcher_email')
mandrill_api = config.get('seekorsurvey', 'mandrill_api')
mandrill_email = config.get('seekorsurvey', 'mandrill_email')
twilio_account_sid = config.get('seekorsurvey', 'twilio_account_sid')
twilio_auth_token = config.get('seekorsurvey', 'twilio_auth_token')
surveygizmo_credentials = config.get('seekorsurvey', 'surveygizmo_credentials')
surveygizmo_surveyresponse = config.get('seekorsurvey', 'surveygizmo_surveyresponse')
opening_line = config.get('seekorsurvey', 'opening_line')

twilioclient = twilio.rest.TwilioRestClient(twilio_account_sid, twilio_auth_token)
mandrillclient = mandrill.Mandrill(mandrill_api)

app = Flask(__name__)

@app.route("/incoming-call", methods=['GET', 'POST'])
def handle_incoming_call():
    """A participant dials in"""
    researcher_index = int(request.values.get('ridx', 0))
    researcher_call_status = request.values.get('DialCallStatus', None)

    resp = twilio.twiml.Response()
    if researcher_call_status != "completed":
        if researcher_index == 0:
            resp.say(opening_line)
            resp.say("Let me try to find a researcher to take your call.")
        elif researcher_index > 0 and researcher_index < len(researcher_numbers):
            resp.say("Sorry, that researcher wasn't available, let me try someone else.")
    
        if researcher_index < len(researcher_numbers):
            resp.say('All calls are recorded.')
            with resp.dial(action='/incoming-call?ridx={}'.format(researcher_index+1), callerId=twilio_number, timeout=researcher_voicemail_timeout, record='record-from-answer') as r:
                r.number(researcher_numbers[researcher_index], url='/screen-researcher')
        else:
            resp.redirect('/survey-or-callback')
    else:
        voicemail = request.values.get('RecordingUrl', None)
        
        if voicemail != None:
            mail_text = '''Here is a new survey recording.

{}
'''.format(voicemail)
            
            try:
                message = {'to': [{'email': researcher_email}],
                           'from_email': mandrill_email,
                           'subject': '[seekorsurvey] New survey recording',
                           'text': mail_text}
                result = mandrillclient.messages.send(message=message)
            except mandrill.Error, e:
                print 'A mandrill error occurred: %s - %s' % (e.__class__, e)
                raise
    
        resp.hangup()
        
    return str(resp)

@app.route("/screen-researcher", methods=['GET', 'POST'])
def handle_screen_researcher():
    """See if a researcher can take the call"""

    resp = twilio.twiml.Response()
    with resp.gather(numDigits=1, action="/connect-researcher", method="POST") as g:
        g.say("Press any button to conduct a survey.")
    resp.hangup()

    return str(resp)

@app.route("/connect-researcher", methods=['GET', 'POST'])
def handle_connect_researcher():
    """Dummy connection URL"""

    resp = twilio.twiml.Response()
    resp.say("Connecting to research participant.")
    return str(resp)

@app.route('/survey-or-callback', methods=['GET', 'POST'])
def handle_survey_or_callback():
    """Prompt to take the survey or get called back"""
    tries = int(request.values.get('try', 0))

    resp = twilio.twiml.Response()
    if tries == 0:
        resp.say("Sorry, no researchers are available to conduct the survey personally.")
        with resp.gather(numDigits=1, action="/which-survey-or-callback", method="POST") as g:
            g.say('Would you like to use our automated system to take the survey?  Press 1 to use our automated system, or press 2 to have a researcher call you back.')
    elif tries == 1:
        with resp.gather(numDigits=1, action="/which-survey-or-callback", method="POST") as g:
            g.say('If you\'d like to use our automated system to take the survey, press 1.  To have a researcher call you back, press 2.')
    elif tries == 2:
        with resp.gather(numDigits=1, action="/which-survey-or-callback", method="POST") as g:
            g.say('Please press 1 to use our automated system to take the survey, or press 2 to have a researcher call you back.')
    else:
        resp.say('Sorry, I couldn\'t hear any button presses.  Please try your call again later.')
        resp.hangup()
        
    resp.redirect('/survey-or-callback?try={}'.format(tries+1))
    return str(resp)

@app.route('/which-survey-or-callback', methods=['GET', 'POST'])
def handle_which_survey_or_callback():
    """Did the user choose to take the survey, or get called back?"""
    digit_pressed = request.values.get('Digits', None)
    
    resp = twilio.twiml.Response()
    if int(digit_pressed) == 1:
        resp.redirect('/start-survey')
    elif int(digit_pressed) == 2:
        resp.redirect('/callback-recording')
    else:
        resp.redirect('/survey-or-callback')
    
    return str(resp)

@app.route('/callback-recording', methods=['GET', 'POST'])
def handle_callback_recording():
    """Record a message for callback"""
    resp = twilio.twiml.Response()
    
    resp.say("After the tone, please say your name, hospital system or practice group, and a number to call you back at, and a researcher will return your call as soon as possible.  Thank you!")
    resp.record(maxLength=120, action="/callback-voicemail", transcribe=True, transcribeCallback="/callback-transcription")
    resp.say("Sorry, I couldn't hear your message. Please try your call again later.")
    resp.hangup()
    
    return str(resp)

@app.route("/callback-voicemail", methods=['GET', 'POST'])
def handle_callback_voicemail():
    """Goodbye caller(s)?"""

    resp = twilio.twiml.Response()
    resp.say("Thank you for calling. A researcher will return your call soon.  Goodbye.")
    resp.hangup()
    return str(resp)

@app.route("/callback-transcription", methods=['GET', 'POST'])
def handle_callback_transcription():
    """Notify via email"""
    from_number = request.values.get('From', None)
    voicemail = request.values.get('RecordingUrl', None)
    transcript_status = request.values.get('TranscriptionStatus', None)
    
    mail_text = '''Here is a new callback request from {}.

Recording: {}

'''.format(from_number, voicemail)
    if (transcript_status == "completed"):
        mail_text = mail_text + """Transcription:

{}
""".format(request.values.get('TranscriptionText', None))
    
    try:
        message = {'to': [{'email': researcher_email}],
                   'from_email': mandrill_email,
                   'subject': '[seekorsurvey] New callback request',
                   'text': mail_text}
        result = mandrillclient.messages.send(message=message)
    except mandrill.Error, e:
        print 'A mandrill error occurred: %s - %s' % (e.__class__, e)
        raise
    
    resp = twilio.twiml.Response()
    resp.hangup()
    return str(resp)

@app.route("/start-survey", methods=['GET', 'POST'])
def handle_start_survey():
    """Create new SurveyGizmo response"""
    call_sid = request.values.get('CallSid', None)

    resp = twilio.twiml.Response()
    payload = {'user:md5': surveygizmo_credentials, '_method': 'PUT', 'data[19][value]': call_sid}
    r = requests.get(surveygizmo_surveyresponse, params=payload)
    if r.status_code != 200:
        resp.say("Sorry, I'm having trouble connecting to the automated system.")
        resp.redirect("/callback-recording")
        
    sg = r.json()
    sg_survey_id = int(sg['data']['responseID'])
        
    resp.redirect("/survey-01-name?sgid={}".format(sg_survey_id))
    return str(resp)

@app.route("/survey-01-name", methods=['GET', 'POST'])
def handle_survey_01_name():
    """Say the name and update SurveyGizmo"""
    sg_survey_id = request.values.get('sgid', None)
    
    resp = twilio.twiml.Response()
    if sg_survey_id == None:
        resp.say("Sorry, I'm having trouble connecting to the automated system.")
        resp.redirect("/callback-recording")
    
    resp.say("Question 1.  What is your name?")
    resp.record(maxLength=120, action="/recording-01-name?sgid={}".format(sg_survey_id), transcribe=True, transcribeCallback="/transcription-01-name?sgid={}".format(sg_survey_id))
    resp.say("Sorry, I couldn't hear your name.")
    resp.redirect("/callback-recording")
    
    return str(resp)

@app.route("/recording-01-name", methods=['GET', 'POST'])
def handle_recording_01_name():
    """When recording ends, redirect to next question"""
    sg_survey_id = request.values.get('sgid', None)

    resp = twilio.twiml.Response()
    if sg_survey_id == None:
        resp.say("Sorry, I'm having trouble connecting to the automated system.")
        resp.redirect("/callback-recording")
    else:
        resp.say("Thank you!  Next question.")
        resp.redirect("/survey-02-feelings?sgid={}".format(sg_survey_id))
    return str(resp)

@app.route("/transcription-01-name", methods=['GET', 'POST'])
def handle_transcription_01_name():
    """When transcription returns, insert it into the survey"""
    sg_survey_id = request.values.get('sgid', None)
    voicemail = request.values.get('RecordingUrl', 'No transcript or recording!')
    participant_name = request.values.get('TranscriptionText', voicemail)
    
    payload = {'user:md5': surveygizmo_credentials, '_method': 'POST', 'data[17][value]': participant_name}
    r = requests.get('{}/{}'.format(surveygizmo_surveyresponse, sg_survey_id), params=payload)
    if r.status_code != 200:
        print 'A SurveyGizmo error occurred, survey {}, question {}, HTTP status {}'.format(sg_survey_id, 1, r.status_code)
        raise
        
    resp = twilio.twiml.Response()
    return str(resp)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=6600)
