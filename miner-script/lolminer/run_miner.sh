#!/bin/bash

#################################
## Begin of user-editable part ##
#################################

PROFILE=EXAMPLE1	

#################################
##  End of user-editable part  ##
#################################

cd "$(dirname "$0")"
while true
do
  ./lolMiner -profile=$PROFILE $@
  if [ $? -eq 134 ]
  then
    break
  fi
done
