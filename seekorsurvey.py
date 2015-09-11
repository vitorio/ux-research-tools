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

@app.route('/incoming-call-human-or-robot', methods=['GET', 'POST'])
def handle_incoming_call_human_or_robot():
    """Prompt to talk to a person or talk to a robot"""
    tries = int(request.values.get('try', 0))

    resp = twilio.twiml.Response()
    if tries == 0:
        resp.say(opening_line, voice="alice", language="en-GB")
        with resp.gather(numDigits=1, action="/which-human-or-robot", method="POST") as g:
            g.say("If you'd like to take the survey by talking with a researcher, press 1.", voice="alice", language="en-GB")
            g.say("If you'd like to take the survey by using your phone, press 2.", voice="alice", language="en-GB")
            g.say("If you're calling for some other reason and would like to leave a message, press 3.", voice="alice", language="en-GB")
    elif tries == 1:
        with resp.gather(numDigits=1, action="/which-human-or-robot", method="POST") as g:
            g.say("To take the CMGA user survey by talking with a researcher, please press 1.", voice="alice", language="en-GB")
            g.say("To take the CMGA user survey by using your phone, please press 2.", voice="alice", language="en-GB")
            g.say("To leave a message for a researcher, please press 3.", voice="alice", language="en-GB")
    elif tries == 2:
        with resp.gather(numDigits=1, action="/which-human-or-robot", method="POST") as g:
            g.say("Please press 1 if you'd like to take the CMGA user survey by talking with a researcher.", voice="alice", language="en-GB")
            g.say("Please press 2 if you'd like to take the CMGA user survey by using your phone.", voice="alice", language="en-GB")
            g.say("Please press 3 to leave a message for a researcher to return your call.", voice="alice", language="en-GB")
    else:
        resp.say("I'm sorry, I couldn't hear any button selections.", voice="alice", language="en-GB")
        resp.redirect('/callback-recording')
        
    resp.redirect('/incoming-call-human-or-robot?try={}'.format(tries+1))
    return str(resp)

@app.route('/which-human-or-robot', methods=['GET', 'POST'])
def handle_which_human_or_robot():
    """Did the user choose to a human or a robot?"""
    digit_pressed = request.values.get('Digits', None)
    
    resp = twilio.twiml.Response()
    if int(digit_pressed) == 1:
        resp.redirect('/seek-researcher')
    elif int(digit_pressed) == 2:
        resp.redirect('/fake-survey')
    elif int(digit_pressed) == 3:
        resp.redirect('/callback-recording')
    else:
        resp.redirect('/incoming-call-human-or-robot?try=1')
    
    return str(resp)

@app.route("/seek-researcher", methods=['GET', 'POST'])
def handle_seek_researcher():
    """Find a researcher to talk with"""
    researcher_index = int(request.values.get('ridx', 0))
    researcher_call_status = request.values.get('DialCallStatus', None)

    resp = twilio.twiml.Response()
    if researcher_call_status != "completed":
        if researcher_index == 0:
            resp.say("Let me try to find a researcher to take your call.  I'll try up to three different researchers, and you'll hear their line ringing each time.  This call will be recorded.", voice="alice", language="en-GB")
        elif researcher_index > 0 and researcher_index < (len(researcher_numbers) - 1):
            resp.say("I'm sorry, that researcher wasn't available, let me try someone else.  This call will be recorded.", voice="alice", language="en-GB")
        elif researcher_index == (len(researcher_numbers) - 1):
            resp.say("I'm sorry, that researcher wasn't available either.  Let me try just one more.  This call will be recorded.", voice="alice", language="en-GB")
    
        if researcher_index < len(researcher_numbers):
            with resp.dial(action='/seek-researcher?ridx={}'.format(researcher_index+1), callerId=twilio_number, timeout=researcher_voicemail_timeout, record='record-from-answer') as r:
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

@app.route("/incoming-call", methods=['GET', 'POST'])
def handle_incoming_call():
    """A participant dials in"""
    researcher_index = int(request.values.get('ridx', 0))
    researcher_call_status = request.values.get('DialCallStatus', None)

    resp = twilio.twiml.Response()
    if researcher_call_status != "completed":
        if researcher_index == 0:
            resp.say(opening_line, voice="alice", language="en-GB")
            resp.say("Let me try to find a researcher to take your call.", voice="alice", language="en-GB")
        elif researcher_index > 0 and researcher_index < len(researcher_numbers):
            resp.say("Sorry, that researcher wasn't available, let me try someone else.", voice="alice", language="en-GB")
    
        if researcher_index < len(researcher_numbers):
            resp.say('All calls are recorded.', voice="alice", language="en-GB")
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
        g.say("Press any button to conduct a survey.", voice="alice", language="en-GB")
    resp.hangup()

    return str(resp)

@app.route("/connect-researcher", methods=['GET', 'POST'])
def handle_connect_researcher():
    """Dummy connection URL"""

    resp = twilio.twiml.Response()
    resp.say("I'm connecting you with a participant now. This call will be recorded.", voice="alice", language="en-GB")
    return str(resp)

@app.route('/survey-or-callback', methods=['GET', 'POST'])
def handle_survey_or_callback():
    """Prompt to take the survey or get called back"""
    tries = int(request.values.get('try', 0))

    resp = twilio.twiml.Response()
    if tries == 0:
        resp.say("I apologize, no researchers are available to conduct the survey personally.", voice="alice", language="en-GB")
        with resp.gather(numDigits=1, action="/which-survey-or-callback", method="POST") as g:
            g.say("If you'd like to have a researcher call you back, press 1.", voice="alice", language="en-GB")
            g.say("If you'd like to take the survey by using your phone, press 2.", voice="alice", language="en-GB")
    elif tries == 1:
        with resp.gather(numDigits=1, action="/which-survey-or-callback", method="POST") as g:
            g.say("If you'd like to leave a message for a researcher to call you back, please press 1.", voice="alice", language="en-GB")
            g.say("If you'd like to use your phone to take the survey, please press 2.", voice="alice", language="en-GB")
    elif tries == 2:
        with resp.gather(numDigits=1, action="/which-survey-or-callback", method="POST") as g:
            g.say("Please press 1 to leave a message for a researcher.", voice="alice", language="en-GB")
            g.say("Please press 2 to take the survey by phone.", voice="alice", language="en-GB")
    else:
        resp.say("I'm sorry, I couldn't hear any button selections.", voice="alice", language="en-GB")
        resp.redirect('/callback-recording')
        
    resp.redirect('/survey-or-callback?try={}'.format(tries+1))
    return str(resp)

@app.route('/which-survey-or-callback', methods=['GET', 'POST'])
def handle_which_survey_or_callback():
    """Did the user choose to take the survey, or get called back?"""
    digit_pressed = request.values.get('Digits', None)
    
    resp = twilio.twiml.Response()
    if int(digit_pressed) == 1:
        resp.redirect('/callback-recording')
    elif int(digit_pressed) == 2:
        resp.redirect('/fake-survey')
    else:
        resp.redirect('/survey-or-callback')
    
    return str(resp)

@app.route('/callback-recording', methods=['GET', 'POST'])
def handle_callback_recording():
    """Record a message for callback"""
    resp = twilio.twiml.Response()
    
    resp.say("After the tone, please say your name, hospital system or practice group, and a good time and number to call you back at, and a researcher will return your call as soon as possible.  Thank you!", voice="alice", language="en-GB")
    resp.record(maxLength=120, action="/callback-voicemail", transcribe=True, transcribeCallback="/callback-transcription")
    resp.say("I'm sorry, I couldn't hear your message.", voice="alice", language="en-GB")
    resp.say("Please try your call again later.", voice="alice", language="en-GB")
    resp.say("Goodbye.", voice="alice", language="en-GB")
    resp.hangup()
    
    return str(resp)

@app.route("/callback-voicemail", methods=['GET', 'POST'])
def handle_callback_voicemail():
    """Goodbye caller(s)?"""

    resp = twilio.twiml.Response()
    resp.say("Thank you for your time. A researcher will return your call soon.", voice="alice", language="en-GB")
    resp.say("Goodbye.", voice="alice", language="en-GB")
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

@app.route("/fake-survey", methods=['GET', 'POST'])
def handle_fake_survey():
    """Bomb out"""

    resp = twilio.twiml.Response()
    resp.say("I'm sorry, I'm having trouble connecting to the automated system.", voice="alice", language="en-GB")
    resp.redirect("/callback-recording")
    return str(resp)

@app.route("/start-survey", methods=['GET', 'POST'])
def handle_start_survey():
    """Create new SurveyGizmo response"""
    call_sid = request.values.get('CallSid', None)

    resp = twilio.twiml.Response()
    payload = {'user:md5': surveygizmo_credentials, '_method': 'PUT', 'data[29][value]': call_sid}
    r = requests.get(surveygizmo_surveyresponse, params=payload)
    if r.status_code != 200:
        resp.say("I'm sorry, I'm having trouble connecting to the automated system.", voice="alice", language="en-GB")
        resp.redirect("/callback-recording")
        
    sg = r.json()
    sg_survey_id = int(sg['data']['responseID'])
        
    resp.redirect("/survey-1?sgid={}".format(sg_survey_id))
    return str(resp)

@app.route("/recording-survey-response", methods=['GET', 'POST'])
def handle_recording_survey_response():
    """When recording ends, redirect to next question"""
    sg_survey_id = request.values.get('sgid', None)
    next_question = request.values.get('next', None)

    resp = twilio.twiml.Response()
    if sg_survey_id == None or next_question == None:
        resp.say("I'm sorry, I'm having trouble connecting to the automated system.", voice="alice", language="en-GB")
        resp.redirect("/callback-recording")
    else:
        resp.say("Thank you!  Next question.")
        resp.redirect("/survey-{}?sgid={}".format(next_question, sg_survey_id))
    return str(resp)

@app.route("/transcribing-survey-response", methods=['GET', 'POST'])
def handle_transcribing_survey_response():
    """When transcription returns, insert it into the survey"""
    sg_survey_id = request.values.get('sgid', None)
    sg_question_id = request.values.get('sgq', None)
    voicemail = request.values.get('RecordingUrl', 'No transcript or recording!')
    transcript = request.values.get('TranscriptionText', '(blank)')
    
    participant_response = voicemail
    if transcript != "(blank)":
        participant_response = transcript + ' - ' + voicemail
    
    payload = {'user:md5': surveygizmo_credentials, '_method': 'POST', 'data[{}][value]'.format(sg_question_id): participant_response}
    r = requests.get('{}/{}'.format(surveygizmo_surveyresponse, sg_survey_id), params=payload)
    if r.status_code != 200:
        print 'A SurveyGizmo error occurred, survey {}, question {}, HTTP status {}'.format(sg_survey_id, sg_question_id, r.status_code)
        raise
        
    resp = twilio.twiml.Response()
    return str(resp)

@app.route("/survey-1", methods=['GET', 'POST'])
def handle_survey_1():
    """Software in use"""
    sg_survey_id = request.values.get('sgid', None)
    sg_question_id = 5
    question_number = 1
    tries = int(request.values.get('try', 0))
    
    resp = twilio.twiml.Response()
    if sg_survey_id == None:
        resp.say("I'm sorry, I'm having trouble connecting to the automated system.", voice="alice", language="en-GB")
        resp.redirect("/callback-recording")
    
    if tries < 3:
        resp.say("Question 1.  Think about the previous business day (or today, if it's the end of the day).  Say the software programs you used to do your work?")
        resp.record(maxLength=300, action="/recording-survey-response?sgid={}&next={}".format(sg_survey_id, question_number+1), transcribe=True, transcribeCallback="/transcribing-survey-response?sgid={}&sgq={}".format(sg_survey_id, sg_question_id))
    else:
        resp.say("Sorry, I couldn't hear you.")
        resp.redirect("/callback-recording")
    
    resp.redirect('/survey-{}?sgid={}&try={}'.format(question_number, sg_survey_id, tries+1))
    return str(resp)

@app.route("/survey-2", methods=['GET', 'POST'])
def handle_survey_2():
    """Hardware in use workstation"""
    sg_survey_id = request.values.get('sgid', None)
    sg_question_id = 6
    question_number = 2
    tries = int(request.values.get('try', 0))
    
    resp = twilio.twiml.Response()
    if sg_survey_id == None:
        resp.say("I'm sorry, I'm having trouble connecting to the automated system.", voice="alice", language="en-GB")
        resp.redirect("/callback-recording")
    
    if tries < 3:
        with resp.gather(numDigits=1, action="/gather-{}?sgid={}".format(question_number, sg_survey_id), method="POST") as g:
            g.say("Question 2 is about hardware you used.  Did you use a shared workstation?  Press 1 for yes, or 2 for no.")
    else:
        resp.say('Sorry, I couldn\'t hear any button presses.')
        resp.redirect("/callback-recording")

    resp.redirect('/survey-{}?sgid={}&try={}'.format(question_number, sg_survey_id, tries+1))
    return str(resp)

@app.route('/gather-2', methods=['GET', 'POST'])
def handle_gather_2():
    """Hardware in use workstation"""
    sg_survey_id = request.values.get('sgid', None)
    sg_question_id = 6
    question_number = 2
    digit_pressed = request.values.get('Digits', None)
        
    resp = twilio.twiml.Response()
    sg_option_id = None
    participant_response = False
    if int(digit_pressed) == 1:
        sg_option_id = 10007
        participant_response = True
    elif int(digit_pressed) == 2:
        sg_option_id = 10007
        participant_response = False
    else:
        resp.redirect('/survey-{}?sgid={}'.format(question_number, sg_survey_id))

    if participant_response:
        payload = {'user:md5': surveygizmo_credentials, '_method': 'POST', 'data[{}][{}]'.format(sg_question_id, sg_option_id): participant_response}
        r = requests.get('{}/{}'.format(surveygizmo_surveyresponse, sg_survey_id), params=payload)
        if r.status_code != 200:
            print 'A SurveyGizmo error occurred, survey {}, question {}, HTTP status {}'.format(sg_survey_id, sg_question_id, r.status_code)
            raise
    
    if sg_option_id != None:
        resp.redirect('/survey-{}?sgid={}'.format(question_number+1, sg_survey_id))
        
    return str(resp)

@app.route("/survey-3", methods=['GET', 'POST'])
def handle_survey_3():
    """Hardware in use desktop"""
    sg_survey_id = request.values.get('sgid', None)
    sg_question_id = 6
    question_number = 3
    tries = int(request.values.get('try', 0))
    
    resp = twilio.twiml.Response()
    if sg_survey_id == None:
        resp.say("I'm sorry, I'm having trouble connecting to the automated system.", voice="alice", language="en-GB")
        resp.redirect("/callback-recording")
    
    if tries < 3:
        with resp.gather(numDigits=1, action="/gather-{}?sgid={}".format(question_number, sg_survey_id), method="POST") as g:
            g.say("Did you use a desktop computer?  Press 1 for yes, or 2 for no.")
    else:
        resp.say('Sorry, I couldn\'t hear any button presses.')
        resp.redirect("/callback-recording")

    resp.redirect('/survey-{}?sgid={}&try={}'.format(question_number, sg_survey_id, tries+1))
    return str(resp)

@app.route('/gather-3', methods=['GET', 'POST'])
def handle_gather_3():
    """Hardware in use desktop"""
    sg_survey_id = request.values.get('sgid', None)
    sg_question_id = 6
    question_number = 3
    digit_pressed = request.values.get('Digits', None)
        
    resp = twilio.twiml.Response()
    sg_option_id = None
    participant_response = False
    if int(digit_pressed) == 1:
        sg_option_id = 10008
        participant_response = True
    elif int(digit_pressed) == 2:
        sg_option_id = 10008
        participant_response = False
    else:
        resp.redirect('/survey-{}?sgid={}'.format(question_number, sg_survey_id))

    if participant_response:
        payload = {'user:md5': surveygizmo_credentials, '_method': 'POST', 'data[{}][{}]'.format(sg_question_id, sg_option_id): participant_response}
        r = requests.get('{}/{}'.format(surveygizmo_surveyresponse, sg_survey_id), params=payload)
        if r.status_code != 200:
            print 'A SurveyGizmo error occurred, survey {}, question {}, HTTP status {}'.format(sg_survey_id, sg_question_id, r.status_code)
            raise
    
    if sg_option_id != None:
        resp.redirect('/survey-{}?sgid={}'.format(question_number+1, sg_survey_id))
        
    return str(resp)

@app.route("/survey-4", methods=['GET', 'POST'])
def handle_survey_4():
    """Hardware in use laptop"""
    sg_survey_id = request.values.get('sgid', None)
    sg_question_id = 6
    question_number = 4
    tries = int(request.values.get('try', 0))
    
    resp = twilio.twiml.Response()
    if sg_survey_id == None:
        resp.say("I'm sorry, I'm having trouble connecting to the automated system.", voice="alice", language="en-GB")
        resp.redirect("/callback-recording")
    
    if tries < 3:
        with resp.gather(numDigits=1, action="/gather-{}?sgid={}".format(question_number, sg_survey_id), method="POST") as g:
            g.say("Did you use a laptop?  Press 1 for yes, or 2 for no.")
    else:
        resp.say('Sorry, I couldn\'t hear any button presses.')
        resp.redirect("/callback-recording")

    resp.redirect('/survey-{}?sgid={}&try={}'.format(question_number, sg_survey_id, tries+1))
    return str(resp)

@app.route('/gather-4', methods=['GET', 'POST'])
def handle_gather_4():
    """Hardware in use laptop"""
    sg_survey_id = request.values.get('sgid', None)
    sg_question_id = 6
    question_number = 4
    digit_pressed = request.values.get('Digits', None)
        
    resp = twilio.twiml.Response()
    sg_option_id = None
    participant_response = False
    if int(digit_pressed) == 1:
        sg_option_id = 10009
        participant_response = True
    elif int(digit_pressed) == 2:
        sg_option_id = 10009
        participant_response = False
    else:
        resp.redirect('/survey-{}?sgid={}'.format(question_number, sg_survey_id))

    if participant_response:
        payload = {'user:md5': surveygizmo_credentials, '_method': 'POST', 'data[{}][{}]'.format(sg_question_id, sg_option_id): participant_response}
        r = requests.get('{}/{}'.format(surveygizmo_surveyresponse, sg_survey_id), params=payload)
        if r.status_code != 200:
            print 'A SurveyGizmo error occurred, survey {}, question {}, HTTP status {}'.format(sg_survey_id, sg_question_id, r.status_code)
            raise
    
    if sg_option_id != None:
        resp.redirect('/survey-{}?sgid={}'.format(question_number+1, sg_survey_id))
        
    return str(resp)

@app.route("/survey-5", methods=['GET', 'POST'])
def handle_survey_5():
    """Hardware in use mobile"""
    sg_survey_id = request.values.get('sgid', None)
    sg_question_id = 6
    question_number = 5
    tries = int(request.values.get('try', 0))
    
    resp = twilio.twiml.Response()
    if sg_survey_id == None:
        resp.say("Sorry, I'm having trouble connecting to the automated system.")
        resp.redirect("/callback-recording")
    
    if tries < 3:
        with resp.gather(numDigits=1, action="/gather-{}?sgid={}".format(question_number, sg_survey_id), method="POST") as g:
            g.say("Did you use a mobile device?  Press 1 for yes, or 2 for no.")
    else:
        resp.say('Sorry, I couldn\'t hear any button presses.')
        resp.redirect("/callback-recording")

    resp.redirect('/survey-{}?sgid={}&try={}'.format(question_number, sg_survey_id, tries+1))
    return str(resp)

@app.route('/gather-5', methods=['GET', 'POST'])
def handle_gather_5():
    """Hardware in use mobile"""
    sg_survey_id = request.values.get('sgid', None)
    sg_question_id = 6
    question_number = 5
    digit_pressed = request.values.get('Digits', None)
        
    resp = twilio.twiml.Response()
    sg_option_id = None
    participant_response = False
    if int(digit_pressed) == 1:
        sg_option_id = 10010
        participant_response = True
    elif int(digit_pressed) == 2:
        sg_option_id = 10010
        participant_response = False
    else:
        resp.redirect('/survey-{}?sgid={}'.format(question_number, sg_survey_id))

    if participant_response:
        payload = {'user:md5': surveygizmo_credentials, '_method': 'POST', 'data[{}][{}]'.format(sg_question_id, sg_option_id): participant_response}
        r = requests.get('{}/{}'.format(surveygizmo_surveyresponse, sg_survey_id), params=payload)
        if r.status_code != 200:
            print 'A SurveyGizmo error occurred, survey {}, question {}, HTTP status {}'.format(sg_survey_id, sg_question_id, r.status_code)
            raise
    
    if sg_option_id != None:
        resp.redirect('/survey-{}?sgid={}'.format(question_number+1, sg_survey_id))
        
    return str(resp)



if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=6600)
