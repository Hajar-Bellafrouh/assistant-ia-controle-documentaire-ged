# Crée un environnement virtuel Python dédié au projet, installe toutes les
# dépendances (RAG + Jupyter) et l'enregistre comme kernel Jupyter utilisable
# dans tes notebooks.
#
# Utilisation (dans PowerShell, à la racine du projet) :
#   .\setup_env.ps1
#
# Si PowerShell bloque l'exécution du script, lance d'abord (une seule fois) :
#   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

$ErrorActionPreference = "Stop"

$EnvName = "venv-ged-rag"
$KernelName = "rag-ged"
$KernelDisplayName = "Python (RAG GED)"

Write-Host ">> Création de l'environnement virtuel : $EnvName"
python -m venv $EnvName

Write-Host ">> Activation de l'environnement"
& ".\$EnvName\Scripts\Activate.ps1"

Write-Host ">> Mise à jour de pip"
python -m pip install --upgrade pip

Write-Host ">> Installation des dépendances (requirements.txt)"
pip install -r requirements.txt

Write-Host ">> Enregistrement du kernel Jupyter : $KernelDisplayName"
python -m ipykernel install --user --name=$KernelName --display-name=$KernelDisplayName

Write-Host ""
Write-Host "=========================================================="
Write-Host "Environnement prêt."
Write-Host ""
Write-Host "Pour l'activer manuellement plus tard (nouveau terminal) :"
Write-Host "  .\$EnvName\Scripts\Activate.ps1"
Write-Host ""
Write-Host "Pour lancer Jupyter Lab :"
Write-Host "  jupyter lab"
Write-Host ""
Write-Host "Dans Jupyter, sélectionne le kernel : $KernelDisplayName"
Write-Host "=========================================================="
