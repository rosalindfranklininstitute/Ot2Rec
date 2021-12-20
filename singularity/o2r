#!/bin/bash

if [[ $# == 2 ]]; then
	singularity run --nv --env DISPLAY=$DISPLAY,XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR -B $XDG_RUNTIME_DIR $O2R_SIF $1 $2
elif [[ $# == 3 ]]; then
	singularity run --nv --env DISPLAY=$DISPLAY,XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR -B $XDG_RUNTIME_DIR $O2R_SIF $1 $2 $3
else
	echo "Incorrect number of arguments, see https://github.com/rosalindfranklininstitute/Ot2Rec for command details"
	exit 1
fi

