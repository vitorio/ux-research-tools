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
