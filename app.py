from flask import Flask, render_template, request, redirect, flash
from db import get_connection
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Required for flash messages

def format_datetime(dt):
    if dt:
        return dt.strftime("%d %B %Y, %H:%M")
    return "-"

@app.route('/', methods=["GET", "POST"])
def home():
    if request.method == "POST":
        nip = request.form.get("nip")
        if not nip:
            flash("NIP harus diisi", "error")
            return render_template("home.html")
            
        if nip == "admin":
            return redirect('/admin')
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT Nama, Shift FROM Karyawan WHERE NIP = ?", (nip,))
            row = cursor.fetchone()
            conn.close()

            if row:
                nama, shift = row
                # Get attendance history
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT TOP 5 CheckInTime, CheckOutTime 
                    FROM AttendanceLog 
                    WHERE NIP = ? 
                    ORDER BY CheckInTime DESC
                """, (nip,))
                history = cursor.fetchall()
                conn.close()
                
                formatted_history = []
                for checkin, checkout in history:
                    formatted_history.append({
                        "CheckInTime": format_datetime(checkin),
                        "CheckOutTime": format_datetime(checkout)
                    })
                
                return render_template("attendance.html", 
                                    nip=nip, 
                                    nama=nama, 
                                    shift=shift,
                                    history=formatted_history)
            else:
                flash("NIP tidak ditemukan", "error")
                return render_template("home.html")
        except Exception as e:
            flash(f"Terjadi kesalahan: {str(e)}", "error")
            return render_template("home.html")
            
    return render_template("home.html")

@app.route('/checkin', methods=["POST"])
def checkin():
    nip = request.form.get("nip")
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now()
            today = now.date()
            
            # Cek apakah sudah checkin hari ini
            cursor.execute("""
                SELECT 1 FROM AttendanceLog 
                WHERE NIP = ? AND CAST(CheckInTime AS DATE) = ?
            """, (nip, today))
            
            if cursor.fetchone():
                flash("Anda sudah check-in hari ini", "error")
                return redirect(f"/attendance?nip={nip}")
                
            cursor.execute("INSERT INTO AttendanceLog (NIP, CheckInTime) VALUES (?, ?)", (nip, now))
            conn.commit()
            flash("Check-in berhasil", "success")
    except Exception as e:
        flash(f"Gagal check-in: {str(e)}", "error")
    return redirect(f"/attendance?nip={nip}")

@app.route('/checkout', methods=["POST"])
def checkout():
    nip = request.form.get("nip")
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.now()
        today = now.date()
        
        # Cek apakah sudah checkin hari ini
        cursor.execute("""
            SELECT 1 FROM AttendanceLog 
            WHERE NIP = ? AND CAST(CheckInTime AS DATE) = ? AND CheckOutTime IS NULL
        """, (nip, today))
        
        if not cursor.fetchone():
            flash("Anda belum check-in hari ini atau sudah checkout", "error")
            return redirect(f"/attendance?nip={nip}")
            
        cursor.execute("""
            UPDATE AttendanceLog
            SET CheckOutTime = ?
            WHERE NIP = ? AND CheckOutTime IS NULL AND CAST(CheckInTime AS DATE) = ?
        """, (now, nip, today))
        conn.commit()
        flash("Check-out berhasil", "success")
    except Exception as e:
        flash(f"Gagal check-out: {str(e)}", "error")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
    return redirect(f"/attendance?nip={nip}")

@app.route('/attendance')
def attendance():
    nip = request.args.get('nip')
    if not nip:
        return redirect('/')
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT Nama, Shift FROM Karyawan WHERE NIP = ?", (nip,))
    row = cursor.fetchone()
    
    if not row:
        flash("NIP tidak ditemukan", "error")
        return redirect('/')
    
    nama, shift = row
    
    # Get attendance history
    cursor.execute("""
        SELECT TOP 5 CheckInTime, CheckOutTime 
        FROM AttendanceLog 
        WHERE NIP = ? 
        ORDER BY CheckInTime DESC
    """, (nip,))
    history = cursor.fetchall()
    conn.close()
    
    formatted_history = []
    for checkin, checkout in history:
        formatted_history.append({
            "CheckInTime": format_datetime(checkin),
            "CheckOutTime": format_datetime(checkout)
        })
    
    return render_template("attendance.html", 
                         nip=nip, 
                         nama=nama, 
                         shift=shift,
                         history=formatted_history)

@app.route('/admin')
def admin():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get employee list
    cursor.execute("SELECT NIP, Nama, Shift FROM Karyawan ORDER BY Nama")
    employees = []
    for row in cursor.fetchall():
        nip, nama, shift = row
        employees.append({
            "NIP": nip,
            "Nama": nama,
            "Shift": shift
        })
    
    # Get attendance logs
    cursor.execute("""
        SELECT A.NIP, K.Nama, A.CheckInTime, A.CheckOutTime
        FROM AttendanceLog A
        JOIN Karyawan K ON A.NIP = K.NIP
        ORDER BY A.CheckInTime DESC
    """)
    logs = []
    for row in cursor.fetchall():
        nip, name, checkin, checkout = row
        logs.append({
            "NIP": nip,
            "Name": name,
            "CheckInTime": format_datetime(checkin),
            "CheckOutTime": format_datetime(checkout)
        })
    conn.close()
    return render_template("admin.html", logs=logs, employees=employees)

@app.route('/add_employee', methods=["POST"])
def add_employee():
    nip = request.form.get("nip")
    nama = request.form.get("nama")
    shift = request.form.get("shift")

    # Validate NIP length
    if len(nip) != 12 or not nip.isdigit():
        flash("NIP harus 12 digit angka", "error")
        return redirect('/admin')

    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if NIP already exists
        cursor.execute("SELECT 1 FROM Karyawan WHERE NIP = ?", (nip,))
        if cursor.fetchone():
            flash("NIP sudah terdaftar", "error")
            conn.close()
            return redirect('/admin')
            
        cursor.execute("INSERT INTO Karyawan (NIP, Nama, Shift) VALUES (?, ?, ?)", (nip, nama, shift))
        conn.commit()
        flash("Karyawan berhasil ditambahkan", "success")
    except Exception as e:
        flash(f"Gagal menambahkan karyawan: {str(e)}", "error")
    finally:
        conn.close()
    return redirect('/admin')

@app.route('/logout')
def logout():
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)