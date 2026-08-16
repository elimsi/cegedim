from flask import Flask, jsonify
import subprocess

app = Flask(__name__)

@app.route('/run', methods=['POST'])
def run_dbt():
    try:
        # Run dbt run command
        res = subprocess.run(
            ['dbt', 'run', '--profiles-dir', '/usr/app', '--project-dir', '/usr/app'], 
            capture_output=True, 
            text=True
        )
        return jsonify({
            'stdout': res.stdout,
            'stderr': res.stderr,
            'code': res.returncode,
            'success': res.returncode == 0
        })
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
