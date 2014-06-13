from flask import Flask, request, redirect
import twilio.twiml
import twilio.rest
import ConfigParser
import mandrill

config = ConfigParser.ConfigParser()
config.readfp(open('screener.cfg'))
twilio_number = config.get('screener', 'twilio_number')
researcher_number = config.get('screener', 'researcher_number')
researcher_email = config.get('screener', 'researcher_email')
researcher_voicemail_timeout = config.get('screener', 'researcher_voicemail_timeout')
mandrill_api = config.get('screener', 'mandrill_api')
mandrill_email = config.get('screener', 'mandrill_email')
twilio_account_sid = config.get('screener', 'twilio_account_sid')
twilio_auth_token = config.get('screener', 'twilio_auth_token')

twilioclient = twilio.rest.TwilioRestClient(twilio_account_sid, twilio_auth_token)
mandrillclient = mandrill.Mandrill(mandrill_api)

app = Flask(__name__)

@app.route("/incoming-call", methods=['GET', 'POST'])
def handle_incoming_call():
    """When someone other than me dials in"""
    from_number = request.values.get('From', None)

    resp = twilio.twiml.Response()
    if from_number == researcher_number:
        with resp.gather(action="/researcher-outbound", timeout=30, method="POST") as a:
            a.say("Hello researcher, enter the area code and number to dial followed by pound")
        resp.say("Sorry, I couldn't hear your touch tones. Please try your call again later.")
        resp.hangup()
    else:
        resp.say("Thanks for your interest in our surveys, focus groups, or interviews. Please hold while we try to connect you with a researcher who can answer your questions.")
        #resp.play("http://demo.twilio.com/hellomonkey/monkey.mp3")

        resp.dial(researcher_number, action="/call-researcher", method="POST", callerId=twilio_number, timeout=researcher_voicemail_timeout)

    return str(resp)

@app.route("/incoming-text", methods=['GET', 'POST'])
def handle_incoming_text():
    """When someone other than me dials in"""
    from_number = request.values.get('From', None)
    sms_body = request.values.get('Body', None)

    if from_number == researcher_number:
        researcher_text = sms_body.partition(' ')
        try:
            message = twilioclient.messages.create(to=researcher_text[0], from_=twilio_number, body=researcher_text[2])
        except twilio.TwilioRestException as e:
            message = twilioclient.messages.create(to=researcher_number, from_=twilio_number, body="Error: " + str(e.status) + " " + str(e.code))
    else:
        # Forward the message to the researcher
        message = twilioclient.messages.create(to=researcher_number, from_=twilio_number, body=from_number + " " + sms_body)

    resp = twilio.twiml.Response()
    return str(resp)

@app.route("/call-researcher", methods=['GET', 'POST'])
def handle_call_researcher():
    """Call my cell"""

    dialcallstatus = request.values.get('DialCallStatus', None)
    if (dialcallstatus == "no-answer") or (dialcallstatus == "busy") or (dialcallstatus == "failed"):
        resp = twilio.twiml.Response()
        resp.say("Sorry, all researchers are busy right now. Please leave a message after the tone. Remember to say your name, phone number, and the survey, focus group, or interview you are responding to.  Thank you!")
        resp.record(maxLength="60", action="/subject-voicemail", transcribe=True, transcribeCallback="/subject-transcription")
        resp.say("Sorry, I couldn't hear your message. Please try your call again later.")
        return str(resp)
    else:
        resp = twilio.twiml.Response()
        resp.hangup()
        return str(resp)

@app.route("/subject-voicemail", methods=['GET', 'POST'])
def handle_subject_voicemail():
    """Goodbye caller"""

    resp = twilio.twiml.Response()
    resp.say("Thank you for calling. A researcher will return your call soon.  Goodbye.")
    resp.hangup()
    return str(resp)

@app.route("/subject-transcription", methods=['GET', 'POST'])
def handle_subject_transcription():
    """Notify via email"""
    from_number = request.values.get('From', None)
    voicemail = request.values.get('RecordingUrl', None)
    transcript_status = request.values.get('TranscriptionStatus', None)
    
    mail_text = '''You have a new UX screener voicemail from %s.

Recording: %s

''' % ( from_number, voicemail )
    if (transcript_status == "completed"):
        mail_text = mail_text + """Transcription:

%s
""" % request.values.get('TranscriptionText', None)
    
    #print mail_text
    
    try:
        message = {'to': [{'email': researcher_email}],
                   'from_email': mandrill_email,
                   'subject': 'UX screener voicemail from %s' % from_number,
                   'text': mail_text}
        result = mandrillclient.messages.send(message=message)
    except mandrill.Error, e:
        print 'A mandrill error occurred: %s - %s' % (e.__class__, e)
        raise
    
    #print result
    
    resp = twilio.twiml.Response()
    resp.hangup()
    return str(resp)

@app.route("/researcher-outbound", methods=['GET', 'POST'])
def handle_researcher_outbound():
    """Call a participant"""
    subjectnumber = request.values.get('Digits', None)

    resp = twilio.twiml.Response()
    resp.dial(subjectnumber, action="/researcher-outbound-result", method="POST", callerId=twilio_number, hangupOnStar=True)
    return str(resp)

@app.route("/researcher-outbound-result", methods=['GET', 'POST'])
def handle_researcher_outbound_result():
    """Called a subject"""

    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=6000)
