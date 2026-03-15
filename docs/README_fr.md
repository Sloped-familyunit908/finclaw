# 🐋 FinClaw — Moteur de Trading IA

> **Le premier moteur de trading IA avec un alpha vérifiable et reproductible.**
> Conçu avec une qualité d'ingénierie institutionnelle par un Principal Engineer de Microsoft.

## 📊 Performance

| Métrique | FinClaw | ai-hedge-fund |
|----------|:-----------:|:-------------:|
| **Taux de victoire global (38 actions)** | **25/38 (66%)** | 13/38 (34%) |
| **Alpha moyen** | **-12,2%** | -27,2% |
| **Avance** | **+14,9%** | — |
| **Marchés couverts** | 🇺🇸🇨🇳🇭🇰🇰🇷🇯🇵 | 🇺🇸 uniquement |

## 🏗️ Architecture

- **Moteur de signaux** : Modèle à 6 facteurs (momentum, EMA, RSI, cassure, volume, Bollinger)
- **Détection de régime** : 7 états de marché identifiés automatiquement
- **Gestion des positions** : Stop suiveur, pyramidage, seuil de rentabilité
- **Gestion des risques** : Stop-loss adaptatif selon le régime
- **Suite de tests** : 34 tests de régression

## 🚀 Démarrage rapide

```bash
git clone https://github.com/your-username/FinClaw.git
cd FinClaw
pip install aiohttp yfinance
python tests/test_engine.py
python benchmark_multimarket.py
```

## 🔑 Innovations clés

1. **Protection canal descendant** : Bloque les entrées haussières pendant les tendances baissières de 30 jours
2. **Refroidissement après pertes consécutives** : Évite le whipsaw dans les marchés agités
3. **Dimensionnement « main chaude »** : Augmente la taille après les séries gagnantes
4. **Adaptation au régime** : Tous les paramètres s'adaptent automatiquement aux conditions de marché

---

*Les systèmes de trading doivent être conçus avec de l'ingénierie, pas avec de la chance 🐋*
