#version 120

uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelMatrix;

attribute vec4 p3d_Vertex;
attribute vec3 p3d_Normal;
attribute vec2 p3d_MultiTexCoord0;

varying vec2 uv;
varying vec3 fragPos;
varying vec3 normal;

void main() {
	gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
	uv = p3d_MultiTexCoord0;
	fragPos = vec3(p3d_ModelMatrix * p3d_Vertex);
	normal = p3d_Normal;
}