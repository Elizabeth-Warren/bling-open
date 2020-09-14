# Bling

Bling is a hotline system built on top of Twilio and Help Scout. It accepts incoming SMS messages and calls, routes them to ring phones and create tickets in Help Scout, and allows agents in Help Scout to send SMS replies and call people back.

A single instance of Bling can handle multiple Help Scout Mailboxes, but each Mailbox must have its own Twilio number.

This repository includes code that should be instructive to folks looking to use mobilecommons rather than Twilio as the SMS transport layer :) 

Bling was built by [@benweissmann](https://github.com/benweissmann). And infinite appreciation to [@avrilpearl](https://github.com/avrilpearl) for her help getting it open sourced!

## Setup

1. Install pipenv, then:

        pipenv install -d

2. Run Tests:

        pipenv run test

3. Run server:

        pipenv run server

4. Open http://localhost:5000/ locally

5. (Optional) use ngrok to accept webhooks from the cloud. Install ngrok with `brew install ngrok`, then run `ngrok http 5000`. ngrok will print out an internet-accessible HTTP/S URL that you can point your webhooks to and they'll be forwarded . ngrok will also print out a localhost URL where you can see its web interface where you can see and replay all incoming requests.

## Loading Messages from Mobilecommons

A speculative implementation of a Mobilecommons loaders is included here at `bling/mc_loader.py`.  It'd need some love to get it working in production. Unfortunately, Team Warren no longer has access to Mobilecommons (or the API documentation which lives behind their paywall) so this is as far as we can take it at this point. 

## Original Documenation

### End-User Experience

The end-user experience looks like this:

- Incoming SMS: A supporter texts the hotline number. The text is sent to Help Scout, either in the existing Conversation with that supporter if there is one, or in a new Conversation if this is the first time the supporter has called or texted us. If this is the first time the supporter has called or texted us, they get back a confirmation text letting them know that we've received their text and we'll get back to them shortly. If there is a technical issue, the supporter receives a text saying that we were unable to receive their message and they should try again later or call instead.

- Outgoing SMS: When a Help Scout Agent replies to the conversation in Help Scout, that reply is sent to the supporter via SMS. The SMS comes from the hotline number. The "EW Automations" account leaves a note in the conversation that the reply text was successfully sent (or not, if there was a technical issue with sending the text).

- Incoming calls: A supporter calls the hotline number. A configurable set of phones rings. If someone answers one of the phones, the supporter is connected to that phone. No recording is made, so there's no need for a recording disclaimer. If nobody answers the phones, the supporter is prompted to leave a voicemail. This voicemail recording is sent to Help Scout, either in the existing Conversation with that supporter if there is one, or in a new Conversation if this is the first time the supporter has called or texted us. If this is the first time the supporter has called or texted us, they get back a confirmation text letting them know that we've received their text and we'll get back to them shortly. Within 10 seconds or so, a transcription of the voicemail is also added to the Help Scout conversation. If there is a technical issue, the supporter receives a text saying that we were unable to receive their voicemail and they should try again later or text instead. If there is a technical issue with the transcription, the voicemail recording will still show up in Help Scout.

- Outgoing calls: A custom sidebar widget in Help Scout shows up for any conversations created by Bling with a "Call back" button. When an agent clicks this button, they're taken to a minimal dialer UI where they can input their personal phone number and click "Dial". When they do, they receive a phone call on their personal phone. If they answer, we then call the supporter's phone number and connect the agent and the supporter. From the supporter's perspective, it looks like the call is coming from the hotline number. A note is added by the EW Automations account to the Help Scout Conversation noting the call. The dialer UI remembers the agent's phone number, so they don't need to re-enter it when making more calls (although they can change it at any time).

### Technical Implementation

#### Incoming SMS

The hotline number is a Twilio number. When a text is received, the Twilio number is configured to hit a webhook URL that goes to the bling backend. The bling backend checks to see if there's a Help Scout Conversation with the supporter already that has fewer than 90 messages in it (Help Scout has a hard cap of 100 messages and we want a bit of headroom). If there's not, a new conversation is created. The SMS message is then posted to the Help Scout conversation. Finally, if there were no existing conversations with this supporter, we send them back an automated reply letting them know that we've received their message.

We configure a primary-handler-fails backup for incoming SMSes in Twilio that uses a static TwiML Bin to send back a failure notification to the supporter. We also configure the Twilio webhook URL with `#rc=3&rp=5xx,all` which will make Twilio retry the call 3 times if it gets a connection error, read timeout, or 5xx HTTP status code. We don't attempt to deduplicate these, so the incoming SMS may appear in Help Scout up to 3 times if bling manages to post to Help Scout but errors out before it can reply with a success response to Twilio.

#### Outgoing SMS

Help Scout is configured to deliver webhook notifications about any Agent replies to bling. When bling receives a webhook, it look at which Mailbox the notification is for, and discards the notification if it doesn't correspond to a Mailbox that Bling is configured for.

bling then looks up the submitter of the Help Scout Conversation. If that submitter has a phone number, we clean the text of the Agent's reply (removing whitespace, message signature, and formatting) and send it via SMS back to the submitter. We then use the Help Scout API to add a note to the conversation saying that the outgoing SMS was successfully sent.

#### Incoming Phone Calls

Incoming phone calls are routed to a Twilio Studio flow that rings a configurable set of phone numbers. If there's no answer, the Twilio Studio flow takes a voicemail and then sends an HTTP request with the recording URL to bling. When it's recording the voicemail, we enable transcriptions and also set the transcription callback URL to bling. If the HTTP request submitting the initial audio recording fails, we text back the caller to let them know that their voicemail was not received. We do not handle errors from the transcription submission, but agents in Help Scout will still be able to see that there was a voicemail and access the recording, there just won't be a follow-up message with the transcription.

Posting the recording and transcription bling works exactly the same as Incoming SMS, as described above.

If the Twilio Studio flow is broken, we configure a primary-handler-failed backup for incoming calls in Twilio that uses a static TwiML Bin to text back a failure notification to the supporter. We don't expect to hit this particular failure; it would only occur if Twilio's core phone services are working but Twilio Studio flows are not.

### Setting up a new hotline

- Create a new mailbox in HelpScout.
    - Grant the “EW Automations” account access to the mailbox.
    - In the configuration for the Hotline Dialer custom helpscout app, enable it for the new mailbox
- Create a new phone number in Twilio
- Update the `BLING_MAILBOXES` environment to have the new number/mailbox ID and deploy.
-  In twilio:
    - Copy the Twilio Studio "Bling Dev" flow. Change the CallPhones block to point to the phones you want to ring (or delete CallPhones and CheckIfAnswered and wire directly to VoicemailMessage). Change the VoicemailMessage to be your new message.
    - Configure the Messaging setting "A message comes in" to be a Webhook to: <your endpoint>
    - Configure the Messaging setting "Primary handler fails" to be the TwiML Bin "Bling SMS Error Response"
    - Configure the Voice & Fax setting "A call comes in" to point to the new Twilio Studio flow you built.
    - Configure the Voice & Fax setting "Primary handler fails" to be the TwiML Bin "Bling Call Error Response"

#### Important note about developing Bling

Help Scout doesn't have a way to only receive webhooks from some mailboxes. So when you're
developing Help Scout, you'll be getting webhook events from *all* mailboxes, so you'll need to be very careful to not, e.g.,
send SMS replies for production mailboxes (because then the user would be getting double text messages from both your development
server and production infrastructure).

To help with this, `bling/helpscout/mailboxes.py` read the set of mailboxes from an environment variable, defaulting to only reading from the local development mailbox. Bling will ignore Webhook payloads for mailboxes that don't match the set of mailboxes for the environment.

#### Setting up the local dev environment

- Run bling and ngrok (see the bling README for details)
- Run `pipenv run server` from this directory
- In the webhook settings for Help Scout, copy the secret from the dev webook and then configure a new webhook to point to your ngrok URL + "/bling/helpscout_webhook" with that same secret. Subscribe it to the "Agent reply" event. IMPORTANT: you MUST delete this webhook configuration before shutting down your dev server!
- Edit the "Hotline Dialer LOCAL" custom helpscout app and point it at your ngrok URL
- Edit the "Bling Local" Twilio Studio Flow to point to your ngrok URL in the RecordVoicemail callback URL and the SendRecording target. Save your changes and click "Publish".
- Edit the "Bling local" Twilio number to point to your ngrok URL for the messaging endpoint
