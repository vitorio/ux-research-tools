ux-research-tools
=================

Tools to reduce UX research administrivia

screener.py
-----------

**Scenario:** A screener will be posted online. I will call and email applicants to confirm their survey responses and schedule them for a focus group. They may also want to call me. The number needs to not be my cell phone number, and to collect voicemails and texts when I am not available.

The following use cases are currently supported:

**Use case 1:** An applicant or participant dials in. They are told to hold while the system tries to reach me. The seek timeout is less than 30 seconds so my personal voicemail does not pick up. If I answer, the call is connected. If I do not, the caller is asked to leave a voicemail.

**Use case 2:** An applicant or participant texts. The text is forwarded to me.

**Use case 3:** I dial in. The system prompts me for a number to dial. The number is dialed, with the caller ID shown as the service number, not my personal number.

**Use case 4:** I text in, with the first part of the message being the number to forward the text to. The system sends the text to the applicant or participant whose number I specified, as the service number, not my personal number.

Requires Twilio and Mandrill.

This is currently in production use.

TODO: daemonizing, SSL, signature checking, Twilio exception catching, logging, email notifications, billing niceties, human voice prompts, more robust hold/seeking, support for multiple researchers (in no particular order).

seekorsurvey.py
---------------

**Scenario:** Researchers provide survey participants the option of calling them to take the survey by phone, instead of online.  Participants should be connected with a researcher if one is available, or should be given the option to their phone to take the survey, or to leave a message for a callback.

The following use cases are currently supported:

**Use case 1:** A participant dials in. They are told to hold while the system tries to reach one or more researchers. If a researcher answers _and presses a button to confirm they are not a voicemail or an erroneous response_, they are connected to the participant. All successful connections are recorded.

**Use case 2:** A participant dials in. They are told to hold while the system tries to reach one or more researchers. None are available. The participant is given the option to take the survey by phone, or to have a researcher call them back. The participant chooses the automated system. A new survey response is created using the surveying software, and incrementally updated as the participant responds to questions.

**Use case 3:** A participant dials in. They are told to hold while the system tries to reach one or more researchers. None are available. The participant is given the option to take the survey by phone, or to have a researcher call them back. The participant chooses a callback. They are asked to leave a message, which is emailed to the researcher.

Requires Twilio and Mandrill and SurveyGizmo and Requests and Flask.

Not for production use.

TODO: everything


Public domain
-------------

ux-research-tools - Tools to reduce UX research administrivia

Written in 2014-2015 by Vitorio Miliano <http://vitor.io/>

To the extent possible under law, the author has dedicated all copyright and related and neighboring rights to this software to the public domain worldwide.  This software is distributed without any warranty.

You should have received a copy of the CC0 Public Domain Dedication along with this software.  If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.
