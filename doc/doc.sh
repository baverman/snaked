#!/bin/sh

rm doc.zip
cd _build/html
zip -r ../../doc.zip ./*
