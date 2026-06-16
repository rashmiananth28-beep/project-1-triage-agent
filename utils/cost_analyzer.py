import sqlite3
from utils.token_counter import TokenCounter

class CostAnalyzer:
    """Analyze costs and detect optimization opportunities"""
    
    def __init__(self, db_path: str = "token_logs.db"):
        self.db_path = db_path
    
    def compare_models(self) -> dict:
        """Compare cost efficiency across models"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                model,
                COUNT(*) as calls,
                AVG(total_tokens) as avg_tokens,
                AVG(cost_usd) as avg_cost,
                SUM(cost_usd) as total_cost
            FROM api_calls
            GROUP BY model
            ORDER BY total_cost DESC
        """)
        
        results = cursor.fetchall()
        conn.close()
        
        print("\n📊 MODEL COMPARISON:")
        print("Model\t\tCalls\tAvg Tokens\tAvg Cost\tTotal Cost")
        print("─" * 70)
        
        for model, calls, avg_tokens, avg_cost, total_cost in results:
            print(f"{model}\t{calls}\t{avg_tokens:.0f}\t${avg_cost:.6f}\t${total_cost:.4f}")
    
    def optimization_suggestions(self) -> list:
        """Suggest ways to reduce costs"""
        suggestions = []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check for high output token usage
        cursor.execute("""
            SELECT 
                AVG(output_tokens) as avg_output,
                MAX(output_tokens) as max_output
            FROM api_calls
        """)
        
        avg_output, max_output = cursor.fetchone()
        
        if max_output > avg_output * 2:
            suggestions.append(f"⚠️ Some calls use 2x output tokens ({max_output}). Consider constraining prompts.")
        
        # Check for unnecessary model usage
        cursor.execute("""
            SELECT COUNT(*) FROM api_calls WHERE model = 'fable-5'
        """)
        
        fable_count = cursor.fetchone()[0]
        if fable_count > 0:
            suggestions.append(f"💡 {fable_count} calls used Fable 5. Could Sonnet 4.6 work instead? (Save 65% on output)")
        
        conn.close()
        
        return suggestions