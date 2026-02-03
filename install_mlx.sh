#!/bin/bash
echo "Установка MLX для Apple Silicon..."

# Установка MLX
pip install mlx>=0.18.0

# Установка mlx-lm для моделей
pip install mlx-lm>=0.0.13

echo "Установка завершена!"