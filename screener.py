from flask import Flask, request, redirect
import twilio.twiml
import ConfigParser

config = ConfigParser.ConfigParser()
config.readfp(open('screener.cfg'))
twilio_number = config.get('screener', 'twilio_number')
researcher_number = config.get('screener', 'researcher_number')
researcher_voicemail_timeout = config.get('screener', 'researcher_voicemail_timeout')
mandrill_api = config.get('screener', 'mandrill_api')

app = Flask(__name__)

@app.route("/", methods=['GET', 'POST'])
def hello_monkey():
    """When someone other than me dials in"""
    from_number = request.values.get('From', None)

    resp = twilio.twiml.Response()
    resp.say("Thanks for your interest in our surveys, focus groups, or interviews. Please hold while we try to connect you with a researcher who can answer your questions.")
    #resp.play("http://demo.twilio.com/hellomonkey/monkey.mp3")

    resp.dial(researcher_number, action="/researcher-dial", method="POST", callerId=twilio_number, timeout=researcher_voicemail_timeout)

    return str(resp)

@app.route("/researcher-dial", methods=['GET', 'POST'])
def handle_key():
    """Call my cell"""

    dialcallstatus = request.values.get('DialCallStatus', None)
    if (dialcallstatus == "no-answer") or (dialcallstatus == "busy") or (dialcallstatus == "failed"):
        resp = twilio.twiml.Response()
        resp.say("Sorry, all researchers are busy right now. Please leave a message after the tone. Remember to say your name, phone number, and the survey, focus group, or interview you are responding to.  Thank you!")
        resp.record(maxLength="60", action="/subject-voicemail")
        resp.say("Sorry, I couldn't hear your message. Please try your call again later.")
        return str(resp)
    else:
        resp = twilio.twiml.Response()
        resp.hangup()
        return str(resp)

@app.route("/subject-voicemail", methods=['GET', 'POST'])
def handle_voicemail():
    """Goodbye caller"""

    resp = twilio.twiml.Response()
    resp.say("Thank you for calling. A researcher will return your call soon.  Goodbye.")
    resp.hangup()
    return str(resp)
 
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
