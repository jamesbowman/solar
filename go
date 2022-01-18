# python battery.py
# python power.py ; exit
# ./instant ; exit
time ./docharts ; exit
time python render.py
exit


CUR_WID=$(xdotool getwindowfocus)
for WID in $(xdotool search --onlyvisible --name 'Solar - Google Chrome')
do
  xdotool windowactivate $WID
  xdotool key 'ctrl+r'
done
xdotool windowactivate $CUR_WID
