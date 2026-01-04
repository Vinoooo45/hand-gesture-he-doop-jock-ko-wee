import cv2
import mediapipe as mp
from gtts import gTTS
import pygame
import threading
import time
import os
import warnings
import tempfile

warnings.filterwarnings("ignore")

# Inisialisasi pygame mixer
try:
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    print("✓ Audio system ready")
except Exception as e:
    print(f"⚠️ Audio warning: {e}")

# MediaPipe
mp_drawing = mp.solutions.drawing_utils
mp_hands = mp.solutions.hands

# Cache untuk audio file
audio_cache = {}
temp_files = []

def play_audio(text):
    """Fungsi untuk memainkan suara dengan caching"""
    try:
        # Buat nama file unik
        filename = f"temp_audio_{hash(text)}.mp3"
        temp_files.append(filename)
        
        # Generate audio jika belum ada di cache
        if text not in audio_cache:
            print(f"🔊 Generating audio: {text}")
            tts = gTTS(text=text, lang='id', slow=False)
            tts.save(filename)
            audio_cache[text] = filename
        else:
            filename = audio_cache[text]
        
        # Putar audio
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()
        
        # Tunggu selesai
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
            
    except Exception as e:
        print(f"❌ Audio error: {e}")
        # Fallback: print text ke console
        print(f"[AUDIO]: {text}")

def cleanup_audio():
    """Bersihkan file temporary"""
    for filename in temp_files:
        try:
            if os.path.exists(filename):
                os.remove(filename)
        except:
            pass

def detect_gesture(landmarks):
    """Deteksi gesture tangan dengan lebih banyak pilihan"""
    if not landmarks:
        return None
    
    # Ambil landmark penting
    thumb_tip = landmarks.landmark[4]
    index_tip = landmarks.landmark[8]
    middle_tip = landmarks.landmark[12]
    ring_tip = landmarks.landmark[16]
    pinky_tip = landmarks.landmark[20]
    
    wrist = landmarks.landmark[0]
    thumb_mcp = landmarks.landmark[2]
    index_mcp = landmarks.landmark[5]
    middle_mcp = landmarks.landmark[9]
    ring_mcp = landmarks.landmark[13]
    pinky_mcp = landmarks.landmark[17]
    
    # Deteksi jari terbuka (y coordinate lebih kecil = jari ke atas)
    thumb_up = thumb_tip.y < thumb_mcp.y - 0.1
    index_up = index_tip.y < index_mcp.y - 0.1
    middle_up = middle_tip.y < middle_mcp.y - 0.1
    ring_up = ring_tip.y < ring_mcp.y - 0.1
    pinky_up = pinky_tip.y < pinky_mcp.y - 0.1
    
    # Hitung jari yang terbuka
    fingers = [thumb_up, index_up, middle_up, ring_up, pinky_up]
    count_up = sum(fingers)
    
    # GESTURE DETECTION - TAMBAHAN "HIDUP JOKOWI"
    
    # 1. ✊ TERTUTUP - "Vino"
    if count_up == 0:
        return "Izin"
    
    # 2. ✋ TERBUKA - "Halo"
    elif count_up >= 4:
        return "Halo Mok"
    
    # 3. ☝️ TELUNJUK - "Nama saya"
    elif count_up == 1 and index_up:
        return "hello Sir"
    
    # 4. ✌️ DUA JARI (VICTORY) - "Hidup Jokowi"
    elif count_up == 2 and index_up and middle_up:
        return "Hidup Jokowi!"
    
    # 5. 🤟 LOVE SIGN - "Terimakasih"
    elif count_up == 2 and index_up and pinky_up:
        return "SIr brad pit"
    
    # 6. 👍 JEMPOL - "Keren"
    elif count_up == 1 and thumb_up:
        return "Keren"
    
    # 7. ✊👊 TINJU (dengan thumb di luar) - "Semangat"
    elif count_up == 1 and thumb_up and not any(fingers[1:]):
        return "yes"
    
    # 8. 🤘 METAL SIGN - "Mantap"
    elif count_up == 2 and index_up and pinky_up and not middle_up and not ring_up:
        return "NASIHUY ANJING"
    
    return None

def draw_gesture_info(frame, gesture, color):
    """Gambar informasi gesture di frame"""
    h, w = frame.shape[:2]
    
    # Panel informasi
    cv2.rectangle(frame, (0, 0), (w, 100), (40, 40, 40), -1)
    cv2.rectangle(frame, (0, 0), (w, 100), color, 2)
    
    # Teks gesture besar
    if gesture:
        # Teks utama
        text_size = cv2.getTextSize(gesture, cv2.FONT_HERSHEY_SIMPLEX, 1.5, 3)[0]
        text_x = (w - text_size[0]) // 2
        text_y = 65
        
        # Shadow
        cv2.putText(frame, gesture, (text_x + 3, text_y + 3), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 3, cv2.LINE_AA)
        # Main text
        cv2.putText(frame, gesture, (text_x, text_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, color, 3, cv2.LINE_AA)
        
        # Subtitle
        cv2.putText(frame, "Gesture Detected!", (20, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # Footer info
    cv2.putText(frame, "ESC: Exit | SPACE: Reset", (20, h - 20), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
    
    return frame

def main():
    # Inisialisasi kamera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Tidak bisa membuka kamera!")
        return
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    # Variabel untuk tracking gesture
    last_gesture = None
    last_time = 0
    gesture_cooldown = 2.0  # 2 detik cooldown
    
    # Warna untuk setiap gesture
    gesture_colors = {
        "Vino": (255, 50, 50),           # Biru
        "Halo Mok": (50, 255, 50),           # Hijau  
        "Nama saya": (50, 150, 255),     # Oranye
        "Hidup Jokowi!": (255, 50, 255), # Ungu
        "Terimakasih": (255, 255, 50),   # Kuning
        "Keren": (50, 255, 255),         # Cyan
        "Semangat!": (255, 150, 50),     # Oranye muda
        "Mantap!": (180, 50, 255)        # Pink
    }
    
    # Tampilkan petunjuk
    print("="*60)
    print("🎮 HAND GESTURE RECOGNITION - DENGAN SUARA")
    print("="*60)
    print("\nGESTURE YANG TERSEDIA:")
    print("1. ✊ Tangan mengepal          → 'Vino'")
    print("2. ✋ Tangan terbuka           → 'Halo Mok'")
    print("3. ☝️ Jari telunjuk           → 'Nama saya'")
    print("4. ✌️ Victory sign (2 jari)   → 'Hidup Jokowi!'")
    print("5. 🤟 Love sign               → 'Terimakasih'")
    print("6. 👍 Jempol                  → 'Keren'")
    print("7. ✊👊 Tinju dengan jempol    → 'Semangat!'")
    print("8. 🤘 Metal sign              → 'Mantap!'")
    print("\n🔊 Setiap gesture akan mengeluarkan suara!")
    print("⏱️  Cooldown 2 detik antara suara")
    print("⎋ Tekan ESC untuk keluar")
    print("="*60)
    
    # Inisialisasi MediaPipe Hands
    with mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7
    ) as hands:
        
        print("\n📹 Memulai kamera...")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                print("❌ Gagal membaca frame")
                break
            
            # Flip horizontal (mirror)
            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]
            
            # Convert ke RGB untuk MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb_frame)
            
            current_gesture = None
            
            # Deteksi gesture
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    # Gambar landmarks tangan
                    mp_drawing.draw_landmarks(
                        frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                        mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=3),
                        mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2, circle_radius=2)
                    )
                    
                    # Deteksi gesture
                    current_gesture = detect_gesture(hand_landmarks)
            
            # Gambar info panel
            color = gesture_colors.get(current_gesture, (255, 255, 255))
            frame = draw_gesture_info(frame, current_gesture, color)
            
            # Handle audio playback
            if current_gesture and current_gesture != last_gesture:
                current_time = time.time()
                
                if current_time - last_time > gesture_cooldown:
                    print(f"🎯 Gesture: {current_gesture}")
                    
                    # Mainkan audio di thread terpisah
                    threading.Thread(
                        target=play_audio, 
                        args=(current_gesture,),
                        daemon=True
                    ).start()
                    
                    last_gesture = current_gesture
                    last_time = current_time
            
            # Tampilkan FPS
            fps = cap.get(cv2.CAP_PROP_FPS)
            cv2.putText(frame, f"FPS: {int(fps)}", (w - 100, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Tampilkan cooldown timer
            if last_gesture:
                elapsed = time.time() - last_time
                if elapsed < gesture_cooldown:
                    remaining = gesture_cooldown - elapsed
                    cv2.putText(frame, f"⏳ {remaining:.1f}s", (w - 100, 60), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Tampilkan frame
            cv2.imshow("🎮 Hand Gesture Recognition - 'Hidup Jokowi!' Edition", frame)
            
            # Keyboard controls
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC
                print("\n👋 Program dihentikan")
                break
            elif key == 32:  # SPACE
                last_gesture = None
                print("🔄 Gesture reset")
            elif key == ord('h'):  # H - Help
                print("\n" + "="*60)
                print("PETUNJUK GESTURE:")
                for i, (gesture, _) in enumerate(list(gesture_colors.items())[:4], 1):
                    print(f"{i}. {gesture}")
                print("="*60)
    
    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    cleanup_audio()
    pygame.mixer.quit()
    
    print("\n✅ Program selesai. File temporary dibersihkan.")
    print("="*60)

if __name__ == "__main__":
    main()