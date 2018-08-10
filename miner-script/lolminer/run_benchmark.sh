#!/bin/bash

#################################
## Begin of user-editable part ##
#################################

PROFILE=EXAMPLE1	

#################################
##  End of user-editable part  ##
#################################

cd "$(dirname "$0")"
./lolMiner -benchmark=MNX $@
./lolMiner -benchmark=BTG $@
