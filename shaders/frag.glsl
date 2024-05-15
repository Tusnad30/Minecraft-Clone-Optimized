#version 120

const float cloudSize = 8192.0;
const vec3 lightColor = vec3(1.0, 0.8, 163.0 / 255.0) * 0.8;
const vec3 sunDirection = vec3(-0.5, -1.0, 0.25);

uniform sampler2D p3d_Texture0;
uniform float iTime;
uniform bool cloud;
uniform vec3[200] lightArray;
uniform int lightArrayLen;

varying vec2 uv;
varying vec3 fragPos;
varying vec3 normal;

void main() {
	float dayVal = clamp(cos(iTime * 0.02) * 1.5 + 0.5, 0.2, 1.0);
    vec3 dayCol = vec3(dayVal);

	if (cloud) {
		vec2 muv = vec2(fract(fragPos.x / cloudSize), fract(fragPos.z / cloudSize));
		muv.y += (iTime / cloudSize) * 6.0;

		gl_FragColor = texture2D(p3d_Texture0, muv) * vec4(dayCol, 1.0);
	}
	else {
		vec3 norm = normalize(normal);

		vec3 sAmbient = vec3(0.5);
		vec3 sLightDir = normalize(-sunDirection);
		vec3 sDiffuse = vec3(max(dot(norm, sLightDir), 0.0));

		vec3 lDiffuse = vec3(0.0);
		for (int i = 0; i < lightArrayLen; i++) {
			if (i > 0) {
				float lDistance = length(lightArray[i] - fragPos);
        		float lAttenuation = clamp(-0.15 * lDistance + 1.0, 0.0, 1.0);

				lDiffuse += lightColor * lAttenuation;
			}
		}
		lDiffuse = clamp(lDiffuse, vec3(0.0), lightColor);

		vec3 lightingResult = clamp((sAmbient + sDiffuse) * dayCol + lDiffuse, 0.0, 1.0);

		// if glowstone, no lighting
        if (0.25 < uv.x && uv.x < 0.5 && 0.5 < uv.y && uv.y < 0.75) lightingResult = vec3(1.0);

		gl_FragColor = texture2D(p3d_Texture0, uv) * vec4(lightingResult, 1.0);
	}
}