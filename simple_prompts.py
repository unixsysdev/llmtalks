#!/usr/bin/env python3
import json
from typing import Dict, Any

class SimpleAgent:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
    
    def planning_phase(self, problem: str, temperature: float = 0.7) -> Dict[str, Any]:
        """Simple planning prompt"""
        prompt = f"""You are Agent {self.agent_id}. Respond with ONLY JSON.

{{
  "analysis": "Brief analysis of the problem",  
  "approach": "Your proposed approach",
  "confidence": 0.8
}}

Problem: {problem}"""
        
        # In real implementation, this would call the LLM
        # For now, return a simple response
        return {
            "analysis": "This is a complex 3D problem requiring physics and rendering",
            "approach": "Use Three.js for rendering and a physics engine for bouncing",
            "confidence": 0.8
        }
    
    def solution_phase(self, problem: str, planning: Dict = None, temperature: float = 0.6) -> Dict[str, Any]:
        """Simple solution prompt"""
        prompt = f"""You are Agent {self.agent_id}. Respond with ONLY JSON.

{{
  "overview": "Brief solution description",
  "code": "The complete working solution",
  "confidence": 0.8
}}

Problem: {problem}"""
        
        # Return example solution
        return {
            "overview": "Creating a 3D bouncing balls simulation using Three.js",
            "code": """<!DOCTYPE html>
<html>
<head>
    <title>3D Bouncing Balls</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
</head>
<body>
    <script>
        let scene, camera, renderer;
        let balls = [];
        
        function init() {
            scene = new THREE.Scene();
            camera = new THREE.PerspectiveCamera(75, window.innerWidth/window.innerHeight, 0.1, 1000);
            renderer = new THREE.WebGLRenderer();
            renderer.setSize(window.innerWidth, window.innerHeight);
            document.body.appendChild(renderer.domElement);
            
            // Create balls
            for(let i = 0; i < 50; i++) {
                let geometry = new THREE.SphereGeometry(0.5, 32, 32);
                let material = new THREE.MeshBasicMaterial({color: Math.random() * 0xffffff});
                let ball = new THREE.Mesh(geometry, material);
                ball.position.set(Math.random() * 10 - 5, Math.random() * 10 - 5, Math.random() * 10 - 5);
                scene.add(ball);
                balls.push(ball);
            }
            
            camera.position.z = 15;
            animate();
        }
        
        function animate() {
            requestAnimationFrame(animate);
            
            // Simple bouncing animation
            balls.forEach(ball => {
                ball.position.y += ball.velocityY || 0.01;
                if(ball.position.y > 5) ball.velocityY = -0.01;
                if(ball.position.y < -5) ball.velocityY = 0.01;
            });
            
            renderer.render(scene, camera);
        }
        
        init();
    </script>
</body>
</html>""",
            "confidence": 0.8
        }
    
    def evaluation_phase(self, solutions: Dict) -> Dict[str, Any]:
        """Simple evaluation prompt"""
        prompt = f"""You are Agent {self.agent_id}. Respond with ONLY JSON.

{{
  "evaluations": [
    {{"agent": "agent_a", "score": 0.8, "notes": "Good implementation"}},
    {{"agent": "agent_b", "score": 0.7, "notes": "Average implementation"}},
    {{"agent": "agent_c", "score": 0.9, "notes": "Best solution"}},
    {{"agent": "agent_d", "score": 0.6, "notes": "Needs improvement"}}
  ],
  "best": "agent_c"
}}"""
        
        return {
            "evaluations": [
                {"agent": "agent_a", "score": 0.8},
                {"agent": "agent_b", "score": 0.7},
                {"agent": "agent_c", "score": 0.9},
                {"agent": "agent_d", "score": 0.6}
            ],
            "best": "agent_c",
            "confidence": 0.9
        }
    
    def implementation_phase(self, problem: str) -> Dict[str, Any]:
        """Simple implementation prompt"""
        prompt = f"""You are Agent {self.agent_id}. Respond with ONLY JSON.

{{
  "code": "Final implementation code",
  "description": "What this code does",
  "confidence": 0.95
}}"""
        
        return {
            "code": "# Final implementation would go here",
            "description": "This solves the problem with optimized code",
            "confidence": 0.95
        }