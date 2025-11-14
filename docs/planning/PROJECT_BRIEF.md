# MVP: Cookbook Creator

## Problem

I want to be able to essentially digitize cookbooks using OCR/Vision/NLP and be able essentially be a platform for cookbook publishers, personal cookbook creation from existing recipes, and help to digitize recipes for restaurants. The MVP would mostly just consist of a simple web UI where you can load an image of a
recipe, and the app stores and digitizes it for easy viewing

## Target Users:

* cookbook publishers
* foodies that love cookbooks
* people with large cookbook collections that want to store and digitize them
* restaurants for maintaining their recipes

## Core features

* Process a recipe from an image using OCR/Vision/NLP and standardize the information written in it, and store that in a database
* a database that unifies recipes from lots of different sources
* a simple web ui that allows someone to input an image, and then view the digitized version

## Tech stack and preferred technologies

* Python for the web backend
* Flask for the web framework
* React for the frontend
* Postgres for the database
* Docker and docker compose for easily setting up postgres, etc...

## Success metrics

A functional webpage that a user can input an image to than then converts it to a digitized recipe.

## Other notes
Include type hints everywhere