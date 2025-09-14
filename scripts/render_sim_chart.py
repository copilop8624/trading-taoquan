import json
from pathlib import Path
import matplotlib.pyplot as plt
from typing import Any, Dict

def render_sim_chart(data: Dict[str, Any], out_path: Path) -> Path:
	"""Render cumulative PnL chart from simulation data and save to out_path.

	Args:
		data: Parsed JSON result from /simulate
		out_path: Path to write PNG file

	Returns:
		Path to saved image
	"""
	cum = data.get('cumulative', [])
	preview = data.get('preview', []) or []
	labels = [p.get('date') or str(i) for i,p in enumerate(preview)]

	plt.figure(figsize=(8,4))
	plt.plot(cum, marker='o')
	plt.title('Simulated Cumulative PnL')
	if len(labels) > 0:
		plt.xticks(range(len(labels)), labels, rotation=30)
	plt.tight_layout()
	out_path.parent.mkdir(parents=True, exist_ok=True)
	plt.savefig(out_path)
	plt.close()
	return out_path


if __name__ == '__main__':
	res = Path('scripts') / 'simulate_result.json'
	assert res.exists(), 'simulate_result.json not found in scripts/'
	data = json.loads(res.read_text())
	out = Path('simulate_cumulative.png')
	saved = render_sim_chart(data, out)
	print('Saved', saved)
