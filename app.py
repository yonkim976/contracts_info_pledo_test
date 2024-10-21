from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
import pandas as pd
from io import BytesIO
from datetime import datetime
from collections import defaultdict
from dateutil.relativedelta import relativedelta
from supabase import create_client, Client
import os

app = Flask(__name__)

# Supabase 설정
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

def safe_float(value):
    try:
        return float(value.replace(',', '')) if value else 0.0
    except ValueError:
        return 0.0

def safe_int(value):
    try:
        return int(float(value.replace(',', ''))) if value else 0
    except ValueError:
        return 0

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add_contract', methods=['POST'])
def add_contract():
    # 폼에서 데이터 가져오기
    title = request.form['title']
    business_number = request.form['business_number']
    representative = request.form['representative']
    contract_type = request.form['contract_type']
    product_price = safe_float(request.form['product_price'])
    quantity = safe_int(request.form['quantity'])
    total_amount = safe_float(request.form['total_amount'])
    tax = safe_float(request.form['tax'])
    total_with_tax = safe_float(request.form['total_with_tax'])
    contract_amount = safe_float(request.form['contract_amount'])
    total_installment = safe_float(request.form['total_installment'])
    payment_months = safe_int(request.form['payment_months'])
    start_date = request.form['start_date']

    # Supabase에 데이터 삽입
    supabase.table('contracts').insert({
        'title': title,
        'business_number': business_number,
        'representative': representative,
        'contract_type': contract_type,
        'product_price': product_price,
        'quantity': quantity,
        'total_amount': total_amount,
        'tax': tax,
        'total_with_tax': total_with_tax,
        'contract_amount': contract_amount,
        'total_installment': total_installment,
        'payment_months': payment_months,
        'start_date': start_date
    }).execute()

    return redirect(url_for('index'))

@app.route('/view_contracts')
def view_contracts():
    # Supabase에서 계약 데이터 가져오기
    response = supabase.table('contracts').select('*').execute()
    contracts = response.data

    return render_template('contracts.html', contracts=contracts)

@app.route('/edit_contract/<int:id>', methods=['GET', 'POST'])
def edit_contract(id):
    if request.method == 'POST':
        # 폼에서 데이터 가져오기
        title = request.form['title']
        business_number = request.form['business_number']
        representative = request.form['representative']
        contract_type = request.form['contract_type']
        product_price = safe_float(request.form['product_price'])
        quantity = safe_int(request.form['quantity'])
        total_amount = safe_float(request.form['total_amount'])
        tax = safe_float(request.form['tax'])
        total_with_tax = safe_float(request.form['total_with_tax'])
        contract_amount = safe_float(request.form['contract_amount'])
        total_installment = safe_float(request.form['total_installment'])
        payment_months = safe_int(request.form['payment_months'])
        start_date = request.form['start_date']

        # Supabase에서 데이터 업데이트
        supabase.table('contracts').update({
            'title': title,
            'business_number': business_number,
            'representative': representative,
            'contract_type': contract_type,
            'product_price': product_price,
            'quantity': quantity,
            'total_amount': total_amount,
            'tax': tax,
            'total_with_tax': total_with_tax,
            'contract_amount': contract_amount,
            'total_installment': total_installment,
            'payment_months': payment_months,
            'start_date': start_date
        }).eq('id', id).execute()

        return redirect(url_for('view_contracts'))
    else:
        # Supabase에서 계약 데이터 가져오기
        response = supabase.table('contracts').select('*').eq('id', id).execute()
        contract = response.data[0] if response.data else None

        if contract:
            return render_template('edit_contract.html', contract=contract)
        else:
            return "Contract not found", 404

@app.route('/delete_contract/<int:id>')
def delete_contract(id):
    # Supabase에서 계약 삭제
    supabase.table('contracts').delete().eq('id', id).execute()
    return redirect(url_for('view_contracts'))

@app.route('/payment_record', methods=['GET', 'POST'])
def payment_record():
    if request.method == 'POST':
        # 폼에서 데이터 가져오기
        title = request.form['title']
        business_number = request.form['business_number']
        representative = request.form['representative']
        payer_name = request.form['payer_name']
        payment_account = request.form['payment_account']
        payment_date = request.form['payment_date']
        payment_amount = safe_float(request.form['payment_amount'])
        memo = request.form['memo']

        # Supabase에 데이터 삽입
        supabase.table('payment_records').insert({
            'title': title,
            'business_number': business_number,
            'representative': representative,
            'payer_name': payer_name,
            'payment_account': payment_account,
            'payment_date': payment_date,
            'payment_amount': payment_amount,
            'memo': memo
        }).execute()

        return redirect(url_for('view_payment_records'))
    return render_template('payment_record.html')

@app.route('/view_payment_records')
def view_payment_records():
    # Supabase에서 입금 기록 가져오기
    response = supabase.table('payment_records').select('*').order('payment_date', desc=True).execute()
    records = response.data

    return render_template('view_payment_records.html', records=records)

@app.route('/monthly_installments')
def monthly_installments():
    # Supabase에서 계약 데이터 가져오기
    response = supabase.table('contracts').select('*').execute()
    contracts = response.data

    # 월별 할부금 계산
    monthly_data = defaultdict(float)
    contract_data = []

    for contract in contracts:
        start_date = datetime.strptime(contract['start_date'], '%Y-%m-%d')
        start_month = start_date.strftime('%Y-%m')
        
        contract_monthly = defaultdict(float)
        
        # 1. 계약금을 시작 월에 추가
        monthly_data[start_month] += contract['contract_amount']
        contract_monthly[start_month] += contract['contract_amount']
        
        # 2. 할부금 계산 및 분배
        if contract['payment_months'] > 0:
            monthly_installment = (contract['total_installment'] - contract['contract_amount']) / contract['payment_months']
            for i in range(contract['payment_months']):
                month = (start_date + relativedelta(months=i)).strftime('%Y-%m')
                monthly_data[month] += monthly_installment
                contract_monthly[month] += monthly_installment
        else:
            # 3. 할부기간이 0인 경우 (일시불)
            monthly_data[start_month] += contract['total_installment'] - contract['contract_amount']
            contract_monthly[start_month] += contract['total_installment'] - contract['contract_amount']

        contract_data.append({
            'id': contract['id'],
            'title': contract['title'],
            'representative': contract['representative'],
            'monthly': contract_monthly
        })

    # 월 정렬
    months = sorted(monthly_data.keys())

    return render_template('monthly_installments.html', months=months, monthly_data=monthly_data, contract_data=contract_data)

@app.route('/monthly_revenue')
def monthly_revenue():
    # Supabase에서 입금 기록 가져오기
    response = supabase.table('payment_records').select('*').execute()
    records = response.data

    # 월별 수익 계산
    monthly_revenue = defaultdict(float)
    for record in records:
        month = datetime.strptime(record['payment_date'], '%Y-%m-%d').strftime('%Y-%m')
        monthly_revenue[month] += record['payment_amount']

    # 월 정렬
    months = sorted(monthly_revenue.keys())

    return render_template('monthly_revenue.html', months=months, monthly_revenue=monthly_revenue)

@app.route('/dashboard')
def dashboard():
    # Supabase에서 계약 및 입금 기록 데이터 가져오기
    contracts_response = supabase.table('contracts').select('*').execute()
    payments_response = supabase.table('payment_records').select('*').execute()

    contracts = contracts_response.data
    payments = payments_response.data

    # 월별 할부금 및 수익 계산
    monthly_installments = defaultdict(float)
    monthly_revenue = defaultdict(float)

    for contract in contracts:
        start_date = datetime.strptime(contract['start_date'], '%Y-%m-%d')
        monthly_installment = contract['total_installment'] / contract['payment_months']
        
        for i in range(contract['payment_months']):
            month = (start_date + relativedelta(months=i)).strftime('%Y-%m')
            monthly_installments[month] += monthly_installment

    for payment in payments:
        month = datetime.strptime(payment['payment_date'], '%Y-%m-%d').strftime('%Y-%m')
        monthly_revenue[month] += payment['payment_amount']

    # 월 정렬
    months = sorted(set(list(monthly_installments.keys()) + list(monthly_revenue.keys())))

    return render_template('dashboard.html', months=months, monthly_installments=monthly_installments, monthly_revenue=monthly_revenue)

@app.route('/contract_status')
def contract_status():
    # Supabase에서 계약 및 입금 기록 데이터 가져오기
    contracts_response = supabase.table('contracts').select('*').execute()
    payments_response = supabase.table('payment_records').select('*').execute()

    contracts = contracts_response.data
    payments = payments_response.data

    # 계약 상태 계산
    contract_status = []
    current_date = datetime.now().date()

    for contract in contracts:
        start_date = datetime.strptime(contract['start_date'], '%Y-%m-%d').date()
        end_date = start_date + relativedelta(months=contract['payment_months'])
        
        paid_amount = sum(payment['payment_amount'] for payment in payments if payment['business_number'] == contract['business_number'])
        remaining_amount = max(0, contract['total_with_tax'] - paid_amount)
        
        status = {
            'title': contract['title'],
            'business_number': contract['business_number'],
            'representative': contract['representative'],
            'end_date': end_date.strftime('%Y-%m-%d'),
            'total_amount': contract['total_with_tax'],
            'paid_amount': paid_amount,
            'remaining_amount': remaining_amount,
            'contract_status': '진행중' if current_date <= end_date else '만료'
        }
        
        contract_status.append(status)

    return render_template('contract_status.html', contracts=contract_status)

@app.route('/download_csv')
def download_csv():
    # Supabase에서 계약 데이터 가져오기
    response = supabase.table('contracts').select('*').execute()
    contracts = response.data

    df = pd.DataFrame(contracts)
    output = BytesIO()
    df.to_csv(output, index=False, encoding='utf-8-sig')
    output.seek(0)
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name='contracts.csv')

@app.route('/download_xlsx')
def download_xlsx():
    # Supabase에서 계약 데이터 가져오기
    response = supabase.table('contracts').select('*').execute()
    contracts = response.data

    df = pd.DataFrame(contracts)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    output.seek(0)
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='contracts.xlsx')

@app.route('/autocomplete')
def autocomplete():
    term = request.args.get('term', '')
    
    # Supabase에서 자동완성 데이터 가져오기
    response = supabase.table('contracts').select('title', 'business_number', 'representative').ilike('title', f'%{term}%').execute()
    results = response.data

    return jsonify([{'value': result['title'], 'business_number': result['business_number'], 'representative': result['representative']} for result in results])

@app.route('/download_monthly_csv')
def download_monthly_csv():
    # Supabase에서 계약 데이터 가져오기
    contracts_response = supabase.table('contracts').select('*').execute()
    contracts = contracts_response.data

    # 월별 할부금 계산
    monthly_data = defaultdict(float)

    for contract in contracts:
        start_date = datetime.strptime(contract['start_date'], '%Y-%m-%d')
        monthly_installment = contract['total_installment'] / contract['payment_months']
        
        for i in range(contract['payment_months']):
            month = (start_date + relativedelta(months=i)).strftime('%Y-%m')
            monthly_data[month] += monthly_installment

    # 데이터프레임 생성
    df = pd.DataFrame(list(monthly_data.items()), columns=['Month', 'Installment Amount'])
    df = df.sort_values('Month')

    # CSV 파일 생성
    output = BytesIO()
    df.to_csv(output, index=False, encoding='utf-8-sig')
    output.seek(0)

    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name='monthly_installments.csv'
    )

@app.route('/download_payment_records_csv')
def download_payment_records_csv():
    # Supabase에서 입금 기록 데이터 가져오기
    response = supabase.table('payment_records').select('*').execute()
    records = response.data

    # 데이터프레임 생성
    df = pd.DataFrame(records)

    # CSV 파일 생성
    output = BytesIO()
    df.to_csv(output, index=False, encoding='utf-8-sig')
    output.seek(0)

    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name='payment_records.csv'
    )

@app.route('/download_payment_records_xlsx')
def download_payment_records_xlsx():
    # Supabase에서 입금 기록 데이터 가져오기
    response = supabase.table('payment_records').select('*').execute()
    records = response.data

    # 데이터프레임 생성
    df = pd.DataFrame(records)

    # XLSX 파일 생성
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Payment Records')
    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='payment_records.xlsx'
    )

@app.route('/download_monthly_xlsx')
def download_monthly_xlsx():
    # Supabase에서 계약 데이터 가져오기
    contracts_response = supabase.table('contracts').select('*').execute()
    contracts = contracts_response.data

    # 월 할부금 계산
    monthly_data = defaultdict(float)

    for contract in contracts:
        start_date = datetime.strptime(contract['start_date'], '%Y-%m-%d')
        start_month = start_date.strftime('%Y-%m')
        
        # 1. 계약금을 시작 월에 추가
        monthly_data[start_month] += contract['contract_amount']
        
        # 2. 할부금 계산 및 분배
        if contract['payment_months'] > 0:
            monthly_installment = (contract['total_installment'] - contract['contract_amount']) / contract['payment_months']
            for i in range(contract['payment_months']):
                month = (start_date + relativedelta(months=i)).strftime('%Y-%m')
                monthly_data[month] += monthly_installment
        else:
            # 3. 할부기간이 0인 경우 (일시불)
            monthly_data[start_month] += contract['total_installment'] - contract['contract_amount']

    # 데이터프레임 생성
    df = pd.DataFrame(list(monthly_data.items()), columns=['Month', 'Amount'])
    df = df.sort_values('Month')

    # XLSX 파일 생성
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Monthly Installments')
    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='monthly_installments.xlsx'
    )

@app.route('/api/monthly_income')
def api_monthly_income():
    start_month = request.args.get('start_month', '')
    end_month = request.args.get('end_month', '')

    # Supabase에서 계약 데이터 가져오기
    contracts_response = supabase.table('contracts').select('*').execute()
    contracts = contracts_response.data

    # 월별 할부금 계산
    monthly_data = defaultdict(float)

    for contract in contracts:
        start_date = datetime.strptime(contract['start_date'], '%Y-%m-%d')
        start_month_str = start_date.strftime('%Y-%m')
        
        # 1. 계약금을 시작 월에 추가
        monthly_data[start_month_str] += contract['contract_amount']
        
        # 2. 할부금 계산 및 분배
        if contract['payment_months'] > 0:
            monthly_installment = (contract['total_installment'] - contract['contract_amount']) / contract['payment_months']
            for i in range(contract['payment_months']):
                month = (start_date + relativedelta(months=i)).strftime('%Y-%m')
                monthly_data[month] += monthly_installment
        else:
            # 3. 할부기간이 0인 경우 (일시불)
            monthly_data[start_month_str] += contract['total_installment'] - contract['contract_amount']

    # 필터링
    if start_month and end_month:
        monthly_data = {k: v for k, v in monthly_data.items() if start_month <= k <= end_month}

    # 정렬
    sorted_data = sorted(monthly_data.items())

    return jsonify({
        'labels': [item[0] for item in sorted_data],
        'data': [item[1] for item in sorted_data]
    })

@app.route('/api/monthly_revenue')
def api_monthly_revenue():
    start_month = request.args.get('start_month', '')
    end_month = request.args.get('end_month', '')

    # Supabase에서 입금 기록 가져오기
    response = supabase.table('payment_records').select('*').execute()
    records = response.data

    # 월별 수익 계산
    monthly_revenue = defaultdict(float)
    for record in records:
        month = datetime.strptime(record['payment_date'], '%Y-%m-%d').strftime('%Y-%m')
        monthly_revenue[month] += record['payment_amount']

    # 필터링
    if start_month and end_month:
        monthly_revenue = {k: v for k, v in monthly_revenue.items() if start_month <= k <= end_month}

    # 정렬
    sorted_data = sorted(monthly_revenue.items())

    return jsonify({
        'labels': [item[0] for item in sorted_data],
        'data': [item[1] for item in sorted_data]
    })

@app.route('/download_contract_status_csv')
def download_contract_status_csv():
    try:
        # Supabase에서 계약 및 입금 기록 데이터 가져오기
        contracts_response = supabase.table('contracts').select('*').execute()
        payments_response = supabase.table('payment_records').select('*').execute()

        contracts = contracts_response.data
        payments = payments_response.data

        # 계약 상태 계산
        contract_status = []
        current_date = datetime.now().date()

        for contract in contracts:
            start_date = datetime.strptime(contract['start_date'], '%Y-%m-%d').date()
            end_date = start_date + relativedelta(months=contract['payment_months'])
            
            paid_amount = sum(payment['payment_amount'] for payment in payments if payment['business_number'] == contract['business_number'])
            remaining_amount = max(0, contract['total_with_tax'] - paid_amount)
            
            status = {
                'title': contract['title'],
                'business_number': contract['business_number'],
                'representative': contract['representative'],
                'end_date': end_date.strftime('%Y-%m-%d'),
                'total_amount': contract['total_with_tax'],
                'paid_amount': paid_amount,
                'remaining_amount': remaining_amount,
                'contract_status': '진행중' if current_date <= end_date else '만료'
            }
            
            contract_status.append(status)

        # DataFrame 생성 및 CSV 파일로 변환
        df = pd.DataFrame(contract_status)
        output = BytesIO()
        df.to_csv(output, index=False, encoding='utf-8-sig')
        output.seek(0)
        
        return send_file(output, 
                         mimetype='text/csv', 
                         as_attachment=True, 
                         download_name='contract_status.csv')

    except Exception as e:
        app.logger.error(f'계약 상태 CSV 다운로드 중 오류 발생: {str(e)}')
        return render_template('error.html', error='계약 상태 CSV 다운로드 중 오류가 발생했습니다.')

@app.route('/download_contract_status_xlsx')
def download_contract_status_xlsx():
    try:
        # Supabase에서 계약 및 입금 기록 데이터 가져오기
        contracts_response = supabase.table('contracts').select('*').execute()
        payments_response = supabase.table('payment_records').select('*').execute()

        contracts = contracts_response.data
        payments = payments_response.data

        # 계약 상태 계산 (위의 CSV 함수와 동일한 로직)
        contract_status = []
        current_date = datetime.now().date()

        for contract in contracts:
            start_date = datetime.strptime(contract['start_date'], '%Y-%m-%d').date()
            end_date = start_date + relativedelta(months=contract['payment_months'])
            
            paid_amount = sum(payment['payment_amount'] for payment in payments if payment['business_number'] == contract['business_number'])
            remaining_amount = max(0, contract['total_with_tax'] - paid_amount)
            
            status = {
                'title': contract['title'],
                'business_number': contract['business_number'],
                'representative': contract['representative'],
                'end_date': end_date.strftime('%Y-%m-%d'),
                'total_amount': contract['total_with_tax'],
                'paid_amount': paid_amount,
                'remaining_amount': remaining_amount,
                'contract_status': '진행중' if current_date <= end_date else '만료'
            }
            
            contract_status.append(status)

        # DataFrame 생성 및 XLSX 파일로 변환
        df = pd.DataFrame(contract_status)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
        output.seek(0)
        
        return send_file(output, 
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
                         as_attachment=True, 
                         download_name='contract_status.xlsx')

    except Exception as e:
        app.logger.error(f'계약 상태 XLSX 다운로드 중 오류 발생: {str(e)}')
        return render_template('error.html', error='계약 상태 XLSX 다운로드 중 오류가 발생했습니다.')

@app.route('/edit_payment_record/<int:id>', methods=['GET', 'POST'])
def edit_payment_record(id):
    if request.method == 'POST':
        # 폼에서 데이터 가져오기
        title = request.form['title']
        business_number = request.form['business_number']
        representative = request.form['representative']
        payer_name = request.form['payer_name']
        payment_account = request.form['payment_account']
        payment_date = request.form['payment_date']
        payment_amount = safe_float(request.form['payment_amount'])
        memo = request.form['memo']

        # Supabase에서 데이터 업데이트
        supabase.table('payment_records').update({
            'title': title,
            'business_number': business_number,
            'representative': representative,
            'payer_name': payer_name,
            'payment_account': payment_account,
            'payment_date': payment_date,
            'payment_amount': payment_amount,
            'memo': memo
        }).eq('id', id).execute()

        return redirect(url_for('view_payment_records'))
    else:
        # Supabase에서 입금 기록 데이터 가져오기
        response = supabase.table('payment_records').select('*').eq('id', id).execute()
        record = response.data[0] if response.data else None

        if record:
            return render_template('edit_payment_record.html', record=record)
        else:
            return "Payment record not found", 404

@app.route('/delete_payment_record/<int:id>')
def delete_payment_record(id):
    # Supabase에서 입금 기록 삭제
    supabase.table('payment_records').delete().eq('id', id).execute()
    return redirect(url_for('view_payment_records'))

@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error='페이지를 찾을 수 없습니다.'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error='내부 서버 오류가 발생했습니다.'), 500

if __name__ == '__main__':
    app.run(debug=True)
