#!/usr/bin/env bash

# Stick floating viz timer

terminator -T viz_timer -e "termdown $1" &
sleep 1s
i3-msg '[title=viz_timer]' floating enable
i3-msg '[title=viz_timer]' sticky enable
i3-msg '[title=viz_timer]' resize set 20ppt 20ppt
# Move to slightly below the top-right corner
# (x,y) coord for the top-left corner of the window
# So (100-20)x, 5y
i3-msg '[title=viz_timer]' move position 80ppt 5ppt

