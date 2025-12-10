ACCOUNT_SID=ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
AUTH_TOKEN=your_auth_token_here

curl -s -u "$ACCOUNT_SID:$AUTH_TOKEN" \
  https://api.twilio.com/2010-04-01/Accounts/$ACCOUNT_SID/Messages/MMXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX/Media/MEXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX \
  -o voice_note.ogg

echo "Done! Size:" $(du -h voice_note.ogg | cut -f1)./
