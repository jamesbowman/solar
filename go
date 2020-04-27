# python battery.py
# python renogy_rover.py
# cp index.html style.css *.svg /var/www/html

python render.py

CUR_WID=$(xdotool getwindowfocus)
for WID in $(xdotool search --onlyvisible --name 'Solar - Google Chrome')
do
  xdotool windowactivate $WID
  xdotool key 'ctrl+r'
done
xdotool windowactivate $CUR_WID
