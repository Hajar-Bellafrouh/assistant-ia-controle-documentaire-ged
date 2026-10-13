#!/usr/bin/env bash
# Crée un environnement virtuel Python dédié au projet, installe toutes les
# dépendances (RAG + Jupyter) et l'enregistre comme kernel Jupyter utilisable
# dans tes notebooks.
#
# Utilisation :
#   chmod +x setup_env.sh
#   ./setup_env.sh

set -e

ENV_NAME="venv-ged-rag"
KERNEL_NAME="rag-ged"
KERNEL_DISPLAY_NAME="Python (RAG GED)"

echo ">> Création de l'environnement virtuel : $ENV_NAME"
python3 -m venv "$ENV_NAME"

echo ">> Activation de l'environnement"
source "$ENV_NAME/bin/activate"

echo ">> Mise à jour de pip"
pip install --upgrade pip

echo ">> Installation des dépendances (requirements.txt)"
pip install -r requirements.txt

echo ">> Enregistrement du kernel Jupyter : $KERNEL_DISPLAY_NAME"
python -m ipykernel install --user --name="$KERNEL_NAME" --display-name="$KERNEL_DISPLAY_NAME"

echo ""
echo "=========================================================="
echo "Environnement prêt."
echo ""
echo "Pour l'activer manuellement plus tard :"
echo "  source $ENV_NAME/bin/activate"
echo ""
echo "Pour lancer Jupyter Lab :"
echo "  jupyter lab"
echo ""
echo "Dans Jupyter, sélectionne le kernel : $KERNEL_DISPLAY_NAME"
echo "=========================================================="
