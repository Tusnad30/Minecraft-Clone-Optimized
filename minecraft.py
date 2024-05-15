from ursina import *
from ursina import curve
from ursina.color import rgba
from perlin_numpy import generate_fractal_noise_2d, generate_perlin_noise_3d, generate_perlin_noise_2d
import numpy as np
import json
import zlib
import os

# variables ============================================================

settingsFile = open("settings/settings.json", "r")
settings = json.loads(settingsFile.read())
settingsFile.close()

renderDistance = settings["defaultRenderDistance"]
editorCam = settings["editorCamera"]
genResolution = settings["worldSize"]

chunkSize = settings["chunkSize"]
terrainHeight = settings["terrainHeight"]
heightLimit = settings["heightLimit"]

seed = settings["seed"]
if seed == None:
	seed = np.random.randint(0, 1000000)
renderDistanceChanged = 0
mainMenuOpen = True
canEditBlocks = False
placeBlock = 2
iTime = 0
cloudHeight = heightLimit * 2
lightList = []
updateLights = 0


def repeat(val, maxval):
	return int(val - (val // maxval) * maxval)



# generate world if no save file ============================================================

isSave = os.path.isfile("save.sv")

if isSave == False:
	print("World size: " + str(genResolution))
	print("World seed: " + str(seed))

	treePos = []
	treePos_z = []
	for x in range(genResolution):
		for z in range(genResolution):
			np.random.seed(seed + x * z + 245)
			if np.random.random() > 0.98:
				treePos_z.append(1)
			else: treePos_z.append(0)
		treePos.append(treePos_z)
		treePos_z = []

	cactusPos = []
	cactusPos_z = []
	for x in range(genResolution):
		for z in range(genResolution):
			np.random.seed(seed + x * z + 376)
			if np.random.random() > 0.99:
				cactusPos_z.append(np.random.randint(1, 4))
			else: cactusPos_z.append(0)
		cactusPos.append(cactusPos_z)
		cactusPos_z = []

	np.random.seed(seed)
	noise2d = generate_fractal_noise_2d((genResolution, genResolution), (int(genResolution / 64), int(genResolution / 64)), 4, 0.4, 2, (True, True))
	noise3d = generate_perlin_noise_3d((genResolution, heightLimit, genResolution), (int(genResolution / 16), int(heightLimit / 8), int(genResolution / 16)), (True, True, True))
	biomeNoise = generate_perlin_noise_2d((genResolution, genResolution), (int(genResolution / 256), int(genResolution / 256)), (True, True))

	genData, jt, xt, yt, zt = [], [], [], [], []
	for i in range(round(genResolution / chunkSize)):
		for j in range(round(genResolution / chunkSize)):
			for x in range(chunkSize + 2):
				for y in range(heightLimit):
					for z in range(chunkSize + 2):
						xpos = repeat(x + i * chunkSize, genResolution)
						zpos = repeat(z + j * chunkSize, genResolution)

						# terrain noise
						terrain_pos = round(noise2d[xpos][zpos] * terrainHeight + heightLimit / 2)
						terrain_pos_n = terrain_pos - 1

						if y <= terrain_pos + 5:
							if biomeNoise[xpos][zpos] <= 0:
								if y >= terrain_pos:
									# tree
									if terrain_pos_n < y and y < terrain_pos_n + 4 and treePos[xpos][zpos] == 1:
										zt.append(3) # log
									elif y == terrain_pos_n + 4 and treePos[xpos][zpos] == 1:
										zt.append(4) # leave
									elif y == terrain_pos_n + 5 and treePos[xpos][zpos] == 1:
										zt.append(4) # leave
									elif y == terrain_pos_n + 4 and treePos[repeat(xpos + 1, genResolution)][zpos] == 1:
										zt.append(4) # leave
									elif y == terrain_pos_n + 4 and treePos[repeat(xpos - 1, genResolution)][zpos] == 1:
										zt.append(4) # leave
									elif y == terrain_pos_n + 4 and treePos[xpos][repeat(zpos + 1, genResolution)] == 1:
										zt.append(4) # leave
									elif y == terrain_pos_n + 4 and treePos[xpos][repeat(zpos - 1, genResolution)] == 1:
										zt.append(4) # leave
									else: zt.append(0) # air

								elif y > 0 and y < heightLimit / 2 + terrainHeight and noise3d[xpos][y][zpos] > 0.3:
									zt.append(0) # caves

								elif y < terrain_pos - 3:
									zt.append(2) # stones

								elif terrain_pos >= y:
									zt.append(1) #grass
												
								else: zt.append(0) #air
							else:
								if y >= terrain_pos:
									# cactus
									if terrain_pos_n < y and y <= terrain_pos_n + cactusPos[xpos][zpos] and cactusPos[xpos][zpos] > 0:
										zt.append(6) # cactus
									else: zt.append(0) # air
								
								elif y > 0 and y < heightLimit / 2 + terrainHeight and noise3d[xpos][y][zpos] > 0.3:
									zt.append(0) # caves

								elif y < terrain_pos - 3:
									zt.append(2) # stones

								elif terrain_pos >= y:
									zt.append(5) # sand
												
								else: zt.append(0) # air
						else: zt.append(0) # air

					yt.append(zt)
					zt = []
				xt.append(yt)
				yt = []
			jt.append(xt)
			xt = []
		genData.append(jt)
		jt = []

		printNum = i / round(genResolution / chunkSize)
		print("Generating terrain: " + str(round(printNum * 100)) + "%")

	genData.append([[0, 0, 0]]) # lights list

# load world ============================================================

elif isSave == True:
	saveFile = open("save.sv", "br")
	saveRead = saveFile.read()
	saveFile.close()

	saveReadS = zlib.decompress(saveRead).decode()
	genData = json.loads(saveReadS)

lightList = genData[round(genResolution / chunkSize)]

for i in range(len(lightList)):
	lightList[i] = Vec3(lightList[i][0], lightList[i][1], lightList[i][2])

# shaders ============================================================

mainVertexShader, mainFragmentShader = open("shaders/vert.glsl", "r"), open("shaders/frag.glsl", "r")
mainShader = Shader(language = Shader.GLSL, vertex = mainVertexShader.read(), fragment = mainFragmentShader.read())
mainVertexShader.close(); mainFragmentShader.close()

# all classes ============================================================

class FirstPersonController(Entity):
	def __init__(self, **kwargs):
		self.cursor = Entity(parent=camera.ui, model='quad', color=color.black, scale=.01)
		super().__init__()
		self.speed = 5
		self.height = 1.8
		self.camera_pivot = Entity(parent=self, y=self.height)

		camera.parent = self.camera_pivot
		camera.position = (0,0,0)
		camera.rotation = (0,0,0)
		camera.fov = 90
		mouse.locked = True
		self.mouse_sensitivity = Vec2(40, 40)

		self.gravity = 0.5
		self.grounded = False
		self.jump_height = 1.2
		self.jump_duration = .4
		self.jumping = False
		self.air_time = 0

		for key, value in kwargs.items():
			setattr(self, key ,value)

	def update(self):
		self.rotation_y += mouse.velocity[0] * self.mouse_sensitivity[1]

		self.camera_pivot.rotation_x -= mouse.velocity[1] * self.mouse_sensitivity[0]
		self.camera_pivot.rotation_x= clamp(self.camera_pivot.rotation_x, -90, 90)

		self.direction = Vec3(
			self.forward * (held_keys["w"] - held_keys["s"])
			+ self.right * (held_keys["d"] - held_keys["a"])
			).normalized()

		feet_ray = raycast(self.world_position+Vec3(0,0.5,0), self.direction, ignore=(self,), distance=.5, debug=False)
		head_ray = raycast(self.world_position+Vec3(0,self.height-.1,0), self.direction, ignore=(self,), distance=.5, debug=False)
		if not feet_ray.hit and not head_ray.hit:
			self.position += self.direction * self.speed * time.dt


		if self.gravity:
			ray = raycast(self.world_position+(0,self.height-0.1,0), self.down, ignore=(self,))

			if ray.distance <= self.height-0.05:
				if not self.grounded:
					self.land()
				self.grounded = True
				if ray.world_normal.y > .7 and ray.world_point.y - self.world_y < .5:
					self.y = ray.world_point[1]
				return
			else:
				self.grounded = False

			self.y -= min(self.air_time, ray.distance-.05) * time.dt * 100
			self.air_time += time.dt * .25 * self.gravity


	def input(self, key):
		if key == "space":
			self.jump()

	def jump(self):
		if not self.grounded:
			return

		jray = raycast(self.world_position+(0,self.height,0), self.up, ignore=(self,), distance = self.jump_height)
		if not jray.hit:
			self.grounded = False
			self.animate_y(self.y+self.jump_height, self.jump_duration, resolution=int(1//time.dt), curve=curve.out_quad)
			invoke(self.start_fall, delay=self.jump_duration)

	def start_fall(self):
		self.y_animator.pause()
		self.jumping = False
		self.air_time = 0

	def land(self):
		self.air_time = 0
		self.grounded = True


class Chunk(Entity):
	def __init__(self, position = (0, 0, 0), collider = None):
		verts, tris, uvs, norms = [], [], [], []

		chunkData = genData[repeat(floor(position[0] / chunkSize), round(genResolution / chunkSize))][repeat(floor(position[2] / chunkSize), round(genResolution / chunkSize))]

		trisNumb = 0

		def makePlane(x, y, z, verts_coords, normal, uv):
			nonlocal trisNumb

			verts.append((verts_coords[0] + x, y + verts_coords[1], verts_coords[2] + z))
			verts.append((verts_coords[3] + x, y + verts_coords[4], verts_coords[5] + z))
			verts.append((verts_coords[6] + x, y + verts_coords[7], verts_coords[8] + z))
			verts.append((verts_coords[9] + x, y + verts_coords[10], verts_coords[11] + z))
			tris.append(1 + trisNumb)
			tris.append(2 + trisNumb)
			tris.append(0 + trisNumb)
			tris.append(1 + trisNumb)
			tris.append(3 + trisNumb)
			tris.append(2 + trisNumb)
			trisNumb += 4

			uvs.append((uv[0], uv[1]))
			uvs.append((uv[2], uv[3]))
			uvs.append((uv[4], uv[5]))
			uvs.append((uv[6], uv[7]))
			norms.append(normal)
			norms.append(normal)
			norms.append(normal)
			norms.append(normal)
		
		def getUv(block):
			if block == 1: # grass
				uv = [0,0, 0.25,0, 0,0.25, 0.25,0.25]
			elif block == 2: # stone
				uv = [0.25,0, 0.5,0, 0.25,0.25, 0.5,0.25]
			elif block == 3: # log
				uv = [0.5,0, 0.75,0, 0.5,0.25, 0.75,0.25]
			elif block == 4: # leaves
				uv = [0.75,0, 1,0, 0.75,0.25, 1,0.25]
			elif block == 5: # sand
				uv = [0,0.25, 0.25,0.25, 0,0.5, 0.25,0.5]
			elif block == 6: # cactus
				uv = [0.25,0.25, 0.5,0.25, 0.25,0.5, 0.5,0.5]
			elif block == 7: # stone bricks
				uv = [0.5,0.25, 0.75,0.25, 0.5,0.5, 0.75,0.5]
			elif block == 8: # planks
				uv = [0.75,0.25, 1,0.25, 0.75,0.5, 1,0.5]
			elif block == -1: # glass
				uv = [0,0.5, 0.25,0.5, 0,0.75, 0.25,0.75]
			elif block == 10: # glowstone
				uv = [0.25,0.5, 0.5,0.5, 0.25,0.75, 0.5,0.75]
			else: uv = [0.75,0.75, 1,0.75, 0.75,1, 1,1] # error

			return uv
		
		for x in range(chunkSize):
			for y in range(heightLimit):
				for z in range(chunkSize):
					cur_chunkData = chunkData[x + 1][y][z + 1]
					if not cur_chunkData == 0:
						uv = getUv(cur_chunkData)

						if y < heightLimit - 1 and chunkData[x + 1][y + 1][z + 1] <= 0:
							makePlane(x, y, z, [0,1,0, 1,1,0, 0,1,1, 1,1,1], (0, 1, 0), uv)
						if y > 0 and chunkData[x + 1][y - 1][z + 1] <= 0:
							makePlane(x, y, z, [0,0,1, 1,0,1, 0,0,0, 1,0,0], (0, -1, 0), uv)
						if chunkData[x + 2][y][z + 1] <= 0:
							makePlane(x, y, z, [1,0,0, 1,0,1, 1,1,0, 1,1,1], (1, 0, 0), uv)
						if chunkData[x][y][z + 1] <= 0:
							makePlane(x, y, z, [0,0,1, 0,0,0, 0,1,1, 0,1,0], (-1, 0, 0), uv)
						if chunkData[x + 1][y][z + 2] <= 0:
							makePlane(x, y, z, [1,0,1, 0,0,1, 1,1,1, 0,1,1], (0, 0, 1), uv)
						if chunkData[x + 1][y][z] <= 0:
							makePlane(x, y, z, [0,0,0, 1,0,0, 0,1,0, 1,1,0], (0, 0, -1), uv)

		super().__init__(
			position = position,
			shader = mainShader,
			model = Mesh(vertices = verts, triangles = tris, uvs = uvs, normals = norms),
			texture = atlasTexture,
			collider = collider)

		self.set_shader_input("iTime", iTime)
		self.set_shader_input("cloud", False)
		self.set_shader_input("lightArray", lightList)
		self.set_shader_input("lightArrayLen", len(lightList))

	def update(self):
		self.set_shader_input("iTime", iTime)
		if updateLights > 0:
			self.set_shader_input("lightArray", lightList)
			self.set_shader_input("lightArrayLen", len(lightList))

		# mesh unloading
		if distance_2d(player.position.xz, self.position.xz) > 1.5 * chunkSize and self.collider != None:
			Chunk(position = self.position)
			destroy(self)
			return
		if distance_2d(player.position.xz, self.position.xz) <= 1.5 * chunkSize and self.collider == None:
			Chunk(position = self.position, collider = "mesh")
			destroy(self)
			return
		
		# unload chunk
		xdist, zdist = curChunkx - round(self.position.x / chunkSize), curChunkz - round(self.position.z / chunkSize)
				
		if xdist > renderDistance or zdist > renderDistance or xdist <= -renderDistance or zdist <= -renderDistance:
			destroy(self)


class Clouds(Entity):
	def __init__(self, position = (0, 0, 0)):
		super().__init__(
			position = position,
			shader = mainShader,
			model = "plane",
			texture = cloudsTexture,
			scale = 2048,
			double_sided = True
		)

		self.set_shader_input("iTime", iTime)
		self.set_shader_input("cloud", True)
		self.set_shader_input("lightArray", lightList)
		self.set_shader_input("lightArrayLen", len(lightList))
	
	def update(self):
		self.set_shader_input("iTime", iTime)

		self.position = (player.position.x, cloudHeight, player.position.z)

# main application ============================================================

app = Ursina()

#Texture.default_filtering = "mipmap"

atlasTexture =      Texture("textures/atlas.png")
backgroundTexture = Texture("textures/background.png")
starsTexture =      Texture("textures/stars.png")
hotbar0Texture =    Texture("textures/hotbar0.png")
hotbar1Texture =    Texture("textures/hotbar1.png")
hotbar2Texture =    Texture("textures/hotbar2.png")
hotbar3Texture =    Texture("textures/hotbar3.png")
hotbar4Texture =    Texture("textures/hotbar4.png")
hotbar5Texture =    Texture("textures/hotbar5.png")
hotbar6Texture =    Texture("textures/hotbar6.png")
hotbar7Texture =    Texture("textures/hotbar7.png")
hotbar8Texture =    Texture("textures/hotbar8.png")
hotbar9Texture =    Texture("textures/hotbar9.png")
cloudsTexture =     Texture("textures/clouds.png")


# load chunks and player ============================================================

for x in range(renderDistance * 2):
	for z in range(renderDistance * 2):
		Chunk(position = (x * chunkSize, 0, z * chunkSize))

clouds = Clouds(position = (0, cloudHeight, 0))

if editorCam:
	player = EditorCamera(position = (renderDistance * chunkSize, heightLimit / 2, renderDistance * chunkSize))
else:
	player = FirstPersonController(position = (renderDistance * chunkSize, heightLimit + 2, renderDistance * chunkSize), scale = 0.9)

stars = Sky(model = "sphere", texture = starsTexture, double_sided = True)


# load UI ============================================================

def renderSliderChanged():
	global renderDistance, renderDistanceChanged
	renderDistance = 0
	renderDistanceChanged = 12

def fovSliderChanged():
	camera.fov = fov_slider.value

def sensSliderChanged():
	player.mouse_sensitivity = Vec2(sens_slider.value, sens_slider.value)

def saveGame():
	lightListM = []
	for i in range(len(lightList)):
		lightListM.append([lightList[i][0], lightList[i][1], lightList[i][2]])

	genData[round(genResolution / chunkSize)] = lightListM

	saveWrite = json.dumps(genData).encode()
	saveWriteC = zlib.compress(saveWrite)
	
	saveFile = open("save.sv", "bw")
	saveFile.write(saveWriteC)
	saveFile.close()

def exitGame():
	saveGame()
	application.quit()


exitMenuUI = Entity(parent = camera.ui, scale = (.9, .9), position = (0, 0), color = color.dark_gray, model = "quad")
exitMenuUI2 = Button(position = (0, -0.3, -1), scale = (0.3, 0.1), text = "Save and Exit", on_click = exitGame, model = "quad")
exitMenuUI3 = Button(position = (0, -0.19, -1), scale = (0.3, 0.1), text = "Save", on_click = saveGame, model = "quad")
exitMenuUI4 = Button(scale = (.3, .1), position = (0, 0.36, -1), color = color.dark_gray, pressed_color = color.dark_gray, highlight_color = color.dark_gray, text = "Options...", model = "quad")

render_slider = ThinSlider(min = 1, max = 16, text = "Render Distance", step = 1, default = renderDistance, on_value_changed = renderSliderChanged, position = (-0.15, 0.2, -1))
fov_slider = ThinSlider(min = 30, max = 120, text = "FOV", step = 1, default = 90, on_value_changed = fovSliderChanged, position = (-0.15, 0.1, -1))
sens_slider = ThinSlider(min = 10, max = 200, text = "Sensitivity", step = 1, default = 40, on_value_changed = sensSliderChanged, position = (-0.15, 0.0, -1))

exitMenuUI.enabled, exitMenuUI2.enabled, exitMenuUI3.enabled, exitMenuUI4.enabled, render_slider.enabled, fov_slider.enabled, sens_slider.enabled = False, False, False, False, False, False, False

	
def play():
	global mainMenuOpen, canEditBlocks
	mainMenuUI.enabled, mainMenuUI2.enabled, mainMenuUI3.enabled, mainMenuUI4.enabled, mainMenuOpen = False, False, False, False, False
	canEditBlocks = True
	if editorCam == False:
		mouse.locked = True
		player.air_time = 0
		

mainMenuUI = Entity(parent = camera.ui, position = (0, 0, -3), color = color.white, pressed_color = color.white, highlight_color = color.white, model = "quad", texture = backgroundTexture)
mainMenuUI2 = Entity(parent = camera.ui, position = (0, 0, -2), scale = (10, 10), color = color.black, pressed_color = color.black, highlight_color = color.black, model = "quad")
mainMenuUI3 = Button(position = (0, -0.4, -4), scale = (0.3, 0.1), color = Color(0, 0, 0, 0.8), text = "Exit", on_click = application.quit, model = "quad")
mainMenuUI4 = Button(position = (0, -0.25, -4), scale = (0.3, 0.1), color = Color(0, 0, 0, 0.8), text = "Play", on_click = play, model = "quad")


hotbar = Entity(parent = camera.ui, position = (0, -0.425, 5), scale = (1.41, 0.15, 1), color = hsv(0, 0, 0.25, 0.75), model = "quad")
hotbarslot = Entity(parent = camera.ui, position = (-0.63, -0.425, 4), scale = 0.13, model = "quad", texture = hotbar0Texture)
hotbarslot = Entity(parent = camera.ui, position = (-0.49, -0.425, 4), scale = 0.13, model = "quad", texture = hotbar1Texture)
hotbarslot = Entity(parent = camera.ui, position = (-0.35, -0.425, 4), scale = 0.13, model = "quad", texture = hotbar2Texture)
hotbarslot = Entity(parent = camera.ui, position = (-0.21, -0.425, 4), scale = 0.13, model = "quad", texture = hotbar3Texture)
hotbarslot = Entity(parent = camera.ui, position = (-0.07, -0.425, 4), scale = 0.13, model = "quad", texture = hotbar4Texture)
hotbarslot = Entity(parent = camera.ui, position = (0.07, -0.425, 4), scale = 0.13, model = "quad", texture = hotbar5Texture)
hotbarslot = Entity(parent = camera.ui, position = (0.21, -0.425, 4), scale = 0.13, model = "quad", texture = hotbar6Texture)
hotbarslot = Entity(parent = camera.ui, position = (0.35, -0.425, 4), scale = 0.13, model = "quad", texture = hotbar7Texture)
hotbarslot = Entity(parent = camera.ui, position = (0.49, -0.425, 4), scale = 0.13, model = "quad", texture = hotbar8Texture)
hotbarslot = Entity(parent = camera.ui, position = (0.63, -0.425, 4), scale = 0.13, model = "quad", texture = hotbar9Texture)
hotbarHighlight = Entity(parent = camera.ui, position = (-0.63, -0.425, 4.5), scale = 0.14, color = color.white, model = "quad")

coords = Button(scale = (.3, .1), position = window.top_left, origin = (-0.75, 0.25), color = rgba(255, 255, 255, 0), pressed_color = rgba(255, 255, 255, 0), highlight_color = rgba(255, 255, 255, 0), text = "xyz = ")

mouse.locked = False

# window settings ============================================================

window.title = "Minecraft by Tusnad30"
window.color = rgb(0, 255, 255)
window.render_modes = ("default", "wireframe")
window.fixed_size = True
window.fps_counter.enabled = True
window.borderless = False
window.exit_button.enabled = False
window.cog_button.enabled = False

# keyboard inputs ============================================================

def addLight(pos):
	global updateLights
	position = pos
	position[0] += 0.5
	position[1] += 0.5
	position[2] += 0.5
	lightList.append(position)
	updateLights = 2

def removeLight(pos):
	global updateLights
	position = pos
	position[0] += 0.5
	position[1] += 0.5
	position[2] += 0.5
	for i in range(len(lightList)):
		if position == lightList[i]:
			del lightList[i]
			break
	updateLights = 2


def input(key):
	global canEditBlocks, placeBlock
	# open and close main menu
	if mainMenuOpen == False:
		if key == "escape" and exitMenuUI.enabled == False:
			exitMenuUI.enabled, exitMenuUI2.enabled, exitMenuUI3.enabled, exitMenuUI4.enabled, render_slider.enabled, fov_slider.enabled, sens_slider.enabled = True, True, True, True, True, True, True
			canEditBlocks = False
			mouse.locked = False
		elif key == "escape" and exitMenuUI.enabled == True:
			exitMenuUI.enabled, exitMenuUI2.enabled, exitMenuUI3.enabled, exitMenuUI4.enabled, render_slider.enabled, fov_slider.enabled, sens_slider.enabled = False, False, False, False, False, False, False
			canEditBlocks = True
			mouse.locked = True

	# place and destroy block
	if canEditBlocks:
		if key == "right mouse down":
			hit = raycast(camera.world_position, camera.forward, distance = 6)
			if hit.hit:
				xpos, ypos, zpos = floor(hit.world_point.x + hit.normal.x * 0.5), floor(hit.world_point.y + hit.normal.y * 0.5), floor(hit.world_point.z + hit.normal.z * 0.5)

				hit_cx = floor((hit.world_point.x - hit.normal.x * 0.5) / chunkSize)
				hit_cz = floor((hit.world_point.z - hit.normal.z * 0.5) / chunkSize)

				destroy(hit.entity)

				lposx, lposy, lposz = repeat(xpos, chunkSize), repeat(ypos, heightLimit), repeat(zpos, chunkSize)

				genData[repeat(xpos / chunkSize, round(genResolution / chunkSize))][repeat(zpos / chunkSize, round(genResolution / chunkSize))][lposx + 1][lposy][lposz + 1] = placeBlock
				
				Chunk(position = (hit_cx * chunkSize, 0, hit_cz * chunkSize))

				if placeBlock == 10:
					addLight(Vec3(xpos, ypos, zpos))
		

		if key == "left mouse down":
			hit = raycast(camera.world_position, camera.forward, distance = 6)
			if hit.hit:
				xpos, ypos, zpos = floor(hit.world_point.x - hit.normal.x * 0.5), floor(hit.world_point.y - hit.normal.y * 0.5), floor(hit.world_point.z - hit.normal.z * 0.5)

				hit_cx = floor((hit.world_point.x - hit.normal.x * 0.5) / chunkSize)
				hit_cz = floor((hit.world_point.z - hit.normal.z * 0.5) / chunkSize)

				destroy(hit.entity)

				lposx, lposy, lposz = repeat(xpos, chunkSize), repeat(ypos, heightLimit), repeat(zpos, chunkSize)

				genData[repeat(xpos / chunkSize, round(genResolution / chunkSize))][repeat(zpos / chunkSize, round(genResolution / chunkSize))][lposx + 1][lposy][lposz + 1] = 0

				Chunk(position = (hit_cx * chunkSize, 0, hit_cz * chunkSize))

				removeLight(Vec3(xpos, ypos, zpos))

	
	# hotbar inputs
	if key == "1":
		hotbarHighlight.position = (-0.63, -0.425, 4.5)
		placeBlock = 2
	elif key == "2":
		hotbarHighlight.position = (-0.49, -0.425, 4.5)
		placeBlock = 1
	elif key == "3":
		hotbarHighlight.position = (-0.35, -0.425, 4.5)
		placeBlock = 3
	elif key == "4":
		hotbarHighlight.position = (-0.21, -0.425, 4.5)
		placeBlock = 4
	elif key == "5":
		hotbarHighlight.position = (-0.07, -0.425, 4.5)
		placeBlock = 5
	elif key == "6":
		hotbarHighlight.position = (0.07, -0.425, 4.5)
		placeBlock = 6
	elif key == "7":
		hotbarHighlight.position = (0.21, -0.425, 4.5)
		placeBlock = 7
	elif key == "8":
		hotbarHighlight.position = (0.35, -0.425, 4.5)
		placeBlock = 8
	elif key == "9":
		hotbarHighlight.position = (0.49, -0.425, 4.5)
		placeBlock = -1
	elif key == "0":
		hotbarHighlight.position = (0.63, -0.425, 4.5)
		placeBlock = 10


# main application loop ============================================================

curChunkx, curChunkz = renderDistance, renderDistance
lchunk_px, lchunk_nx, lchunk_pz, lchunk_nz = 0, 0, 0, 0

def update():
	global curChunkx, curChunkz, lchunk_px, lchunk_nx, lchunk_pz, lchunk_nz, renderDistanceChanged, renderDistance, iTime, updateLights
	iTime += time.dt

	# chunk loading
	curChunkPosx, curChunkPosz = round(player.position.x / chunkSize), round(player.position.z / chunkSize)

	if not curChunkx == curChunkPosx or not curChunkz == curChunkPosz:
		if curChunkPosx > curChunkx:
			lchunk_px = renderDistance * 2
		if curChunkPosx < curChunkx:
			lchunk_nx = renderDistance * 2
		if curChunkPosz > curChunkz:
			lchunk_pz = renderDistance * 2
		if curChunkPosz < curChunkz:
			lchunk_nz = renderDistance * 2

		curChunkx, curChunkz = curChunkPosx, curChunkPosz

	if lchunk_px > 0:
		lchunk_px -= 1
		Chunk(position = ((curChunkx + renderDistance - 1) * chunkSize, 0, (lchunk_px + curChunkz - renderDistance) * chunkSize))
	if lchunk_nx > 0:
		lchunk_nx -= 1
		Chunk(position = ((curChunkx - renderDistance) * chunkSize, 0, (lchunk_nx + curChunkz - renderDistance) * chunkSize))
	if lchunk_pz > 0:
		lchunk_pz -= 1
		Chunk(position = ((lchunk_pz + curChunkx - renderDistance) * chunkSize, 0, (curChunkz + renderDistance - 1) * chunkSize))
	if lchunk_nz > 0:
		lchunk_nz -= 1
		Chunk(position = ((lchunk_nz + curChunkx - renderDistance) * chunkSize, 0, (curChunkz - renderDistance) * chunkSize))

	# teleport player to surface
	if player.position.y < -50:
		player.position = (curChunkx * chunkSize, heightLimit + 2, curChunkz * chunkSize)

	# update modified render distance
	if renderDistanceChanged == 1:
		renderDistance = render_slider.value
		renderDistanceChanged = 0

		for x in range(renderDistance * 2):
			for z in range(renderDistance * 2):
				Chunk(position = ((x + (curChunkx - renderDistance)) * chunkSize, 0, (z + (curChunkz - renderDistance)) * chunkSize))

		player.air_time = 0
	
	elif renderDistanceChanged > 1:
		renderDistanceChanged -= 1

	# update coordinates
	coords.text = "xyz = " + str(round(player.position.x, 2)) + " " + str(round(player.position.y, 2)) + " " + str(round(player.position.z, 2))

	# daylight cycle
	col = np.clip(np.cos(iTime * 0.02) * 1.5 + 0.5, 0, 1)
	window.color = rgb(0, col, col)
	stars.color = rgba(1, 1, 1, 1 - col)
	stars.rotation_z += time.dt * 0.5

	# update lights
	if updateLights > 0:
		updateLights -= 1


app.run()