from datetime import datetime, timedelta

def calculate_required_monthly_investment(target, months, annual_rate):
    """
    Calculates the monthly investment required to reach the target
    Using the future value of an annuity formula: PMT = FV / (((1 + r)^n - 1) / r)
    """
    if months <= 0: return target
    r = (annual_rate / 100) / 12  # Monthly rate
    if r == 0: return target / months
    
    pmt = target / ((( (1 + r)**months ) - 1) / r)
    return pmt

def calculate_ideal_projection(month_number, monthly_investment, annual_rate):
    """
    Calculates the future value with monthly investments and compound interest
    month_number: 0 to N (month 0 = today, month N = end of period)
    """
    r = (annual_rate / 100) / 12  # Monthly rate
    
    future_value = 0
    for i in range(month_number + 1):
        future_value = (future_value + monthly_investment) * (1 + r)
    
    return future_value

def format_currency(value):
    return f"R$ {value:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")

def get_months_labels(start_date=None, count=60):
    if start_date is None:
        start_date = datetime.now()
    
    months = []
    month_names = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    
    current_date = start_date.replace(day=1)
    for _ in range(count):
        label = f"{month_names[current_date.month - 1]} {str(current_date.year)[2:]}"
        months.append(label)
        
        # Move to next month safely
        month = current_date.month
        year = current_date.year
        if month == 12:
            current_date = current_date.replace(year=year + 1, month=1)
        else:
            current_date = current_date.replace(month=month + 1)
            
    return months
