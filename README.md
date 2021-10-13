To clean up the tsds:

    find ~/tsd/ -type f -mmin +1500 | xargs rm
