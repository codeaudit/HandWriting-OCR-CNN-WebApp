import numpy as np
import os
import fnmatch
import re
from PIL import Image
import pickle
import configparser
import keras

HEIGHT = 32
WIDTH = 100

config = configparser.ConfigParser()
config.read('settings.ini')
# Path to image dataset
image_directory = config['paths']['IMAGE_DIRECTORY']

# Name of converted dataset file
datafile = 'dataset.p'

# Path to text file containing 1000 words to learn, one word per line
words = set(open('1-1000.txt').read().split())

def load_data():
	regexp = '[a-zA-Z]+'
	word_data = {}

	try:
		# Attempts to load data from pickle
		word_data = pickle.load(open(datafile, "rb"))
		print('data loaded from {}'.format(datafile))
	except:
		for root, dirnames, filenames in os.walk(image_directory):
			for filename in fnmatch.filter(filenames, '*.jpg'):
				fname = os.path.splitext(filename)[0]
				m = re.search(regexp, fname)
				if(m):
					word = m.group(0).lower()
					if(word in words):
						image_path = os.path.join(root, filename)
						try:
							img = convert_to_pixel_array(image_path)
							if (word not in word_data):
								word_data[word] = {}
								word_data[word]['id'] = len(word_data) - 1
								word_data[word]['points'] = []
							point = {}
							point['filename'] = filename
							point['image_path'] = image_path
							point['pixel_array'] = img
							word_data[word]['points'].append(point)
						except:
							print('image not valid: ', filename)
		# Pickle data so this process doesn't need to be repeated
		pickle.dump(word_data, open(datafile, "wb"))
		print('data saved to {}'.format(datafile))

	global NUM_CLASSES
	NUM_CLASSES = len(word_data)
	return word_data

def convert_to_pixel_array(image_path):
	pixels = []

	im = Image.open(image_path, 'r').resize((WIDTH, HEIGHT), Image.BICUBIC).convert('L')
	pixels = list(im.getdata())

	# Normalize and zero center pixel data
	std_dev = np.std(pixels)
	img_mean = np.mean(pixels)

	pixels = [(pixels[offset:offset+WIDTH]-img_mean)/std_dev for offset in range(0, WIDTH*HEIGHT, WIDTH)]
	pixels = np.array(pixels).astype(np.float32)
	
	return pixels

class WordClassifier:
	def __init__(self, modelPath=None, model=None):
		if (model is not None):
			self.model = model
		elif (modelPath is not None):
			self.model = keras.models.load_model(modelPath)
		else:
			raise ValueError('either model or modelPath must be given')
		self.word_data = pickle.load(open(datafile, 'rb'), encoding='latin1')

	def classify_image(self, image_path):
		try:
			image_pixels = convert_to_pixel_array(image_path)
			image_pixels = np.array(image_pixels)
			inp = np.array([image_pixels])
			inp = inp.reshape(inp.shape[0], 32, 100, 1)

			outp = self.model.predict(inp)[0]
			outp = np.array(outp)

			top5_idx = outp.argsort()[-5:]

			top5_words = [(k, outp[v['id']]) for k, v in self.word_data.items() if v['id'] in top5_idx]
			top5_words = sorted(top5_words, key=lambda x: x[1], reverse=True)

			return top5_words
		except FileNotFoundError:
			print('Image not found at path {}'.format(image_path))
