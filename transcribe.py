#!/usr/bin/env python3
"""
Transcritor de Áudio/Vídeo para SRT usando Whisper
Funciona em Windows e Mac
Otimizado para computadores leves (MacBook Air, etc)
Instala dependências automaticamente se necessário

Uso:
  python transcribe_final.py              # Transcreve arquivos no diretório atual
  python transcribe_final.py /caminho     # Transcreve arquivos no caminho especificado
"""

import os
import sys
import subprocess
import platform
from pathlib import Path
import time
import ssl

def fix_ssl_certificates():
    """Corrige problemas de certificados SSL no Mac"""
    try:
        import certifi
        # Configura SSL para usar certificados do certifi
        os.environ['SSL_CERT_FILE'] = certifi.where()
        os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
        print("🔒 Certificados SSL configurados\n")
    except ImportError:
        # Se certifi não estiver instalado, usa contexto não verificado
        ssl._create_default_https_context = ssl._create_unverified_context
        print("🔒 Certificados SSL configurados (modo compatibilidade)\n")

def install_dependencies():
    """Instala dependências necessárias com barra de progresso"""
    dependencies = ['openai-whisper', 'tqdm', 'certifi']

    print("Verificando dependências...\n")

    for package in dependencies:
        try:
            if package == 'openai-whisper':
                __import__('whisper')
            else:
                __import__(package)
            print(f"✓ {package} já instalado")
        except ImportError:
            print(f"📦 Instalando {package}...")
            print("   (isso pode demorar alguns minutos na primeira vez)")

            # Instala com output visível
            process = subprocess.Popen(
                [sys.executable, '-m', 'pip', 'install', package],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            # Mostra progresso
            for line in process.stdout:
                if 'Downloading' in line or 'Installing' in line or 'Successfully' in line:
                    print(f"   {line.strip()}")

            process.wait()

            if process.returncode == 0:
                print(f"   ✓ {package} instalado com sucesso\n")
            else:
                print(f"   ❌ Erro ao instalar {package}\n")
                sys.exit(1)

    # Verifica ffmpeg
    print("\nVerificando ffmpeg...")
    try:
        result = subprocess.run(['ffmpeg', '-version'],
                              capture_output=True,
                              text=True,
                              timeout=5)
        if result.returncode == 0:
            print("✓ ffmpeg já instalado\n")
            return
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Instruções para instalar ffmpeg
    system = platform.system()
    print("\n⚠️  ffmpeg não encontrado!")
    print("\nPara instalar o ffmpeg:")

    if system == "Darwin":  # Mac
        print("  Mac: brew install ffmpeg")
    elif system == "Windows":
        print("  Windows: choco install ffmpeg")
        print("  ou baixe em: https://ffmpeg.org/download.html")
    else:
        print("  Linux: sudo apt install ffmpeg")

    print("\nDepois de instalar o ffmpeg, execute este script novamente.")
    sys.exit(1)

def format_timestamp(seconds):
    """Converte segundos para formato SRT (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def create_srt(segments, output_file):
    """Cria arquivo SRT a partir dos segmentos transcritos"""
    with open(output_file, 'w', encoding='utf-8') as f:
        for i, segment in enumerate(segments, start=1):
            start_time = format_timestamp(segment['start'])
            end_time = format_timestamp(segment['end'])
            text = segment['text'].strip()

            f.write(f"{i}\n")
            f.write(f"{start_time} --> {end_time}\n")
            f.write(f"{text}\n\n")

def get_optimal_model():
    """Retorna o melhor modelo baseado no sistema

    Modelos disponíveis:
    - tiny: ~1GB RAM, muito rápido, qualidade básica
    - base: ~1GB RAM, rápido, qualidade ok
    - small: ~2GB RAM, bom, qualidade boa
    - medium: ~5GB RAM, lento, qualidade muito boa
    - large-v3: ~10GB RAM, mais lento, MELHOR qualidade
    - turbo: ~6GB RAM, 8x mais rápido que large, qualidade excelente ⚡

    TURBO: Otimização do large-v3 com 809M parâmetros
    - 8x mais rápido que large-v3
    - Degradação mínima de qualidade
    - Funciona bem para português brasileiro
    """
    system = platform.system()

    print("🚀 Usando modelo 'turbo' (8x mais rápido, qualidade excelente)")
    print("   • Baseado em large-v3 com 809M parâmetros")
    print("   • Otimizado para velocidade sem perder qualidade")
    print("   • Perfeito para português brasileiro\n")

    return "turbo"

def transcribe_files(directory=None):
    """Transcreve arquivos de áudio/vídeo para SRT"""
    import whisper
    from tqdm import tqdm
    import torch

    # Define o diretório de trabalho
    if directory:
        work_dir = Path(directory)
        if not work_dir.exists():
            print(f"❌ Erro: Diretório '{directory}' não encontrado.")
            return
        os.chdir(work_dir)
    else:
        work_dir = Path.cwd()

    print(f"\n{'='*60}")
    print(f"Diretório de trabalho: {work_dir}")
    print(f"{'='*60}\n")

    # Seleciona modelo otimizado para o sistema
    model_name = get_optimal_model()

    # Carrega o modelo Whisper
    print(f"⏳ Carregando modelo Whisper '{model_name}'...")
    print("   (primeira execução baixa o modelo - pode demorar)\n")

    model = whisper.load_model(model_name)
    print("✓ Modelo carregado com sucesso!\n")

    # Lista arquivos de áudio/vídeo
    extensions = ['*.mp4', '*.mp3', '*.wav', '*.m4a', '*.flac', '*.avi', '*.mov', '*.mkv', '*.MP4', '*.MP3', '*.WAV']
    video_files = []
    for ext in extensions:
        video_files.extend(Path('.').glob(ext))

    video_files = sorted(set(video_files))  # Remove duplicatas e ordena

    if not video_files:
        print("❌ Nenhum arquivo de áudio/vídeo encontrado no diretório atual.")
        print("\nFormatos suportados: mp4, mp3, wav, m4a, flac, avi, mov, mkv")
        return

    print(f"📂 Encontrados {len(video_files)} arquivo(s) para transcrever\n")

    # Processa cada arquivo
    successful = 0
    skipped = 0
    failed = 0

    for idx, video_file in enumerate(video_files, 1):
        output_file = video_file.with_suffix('.srt')

        # Verifica se já existe
        if output_file.exists():
            print(f"[{idx}/{len(video_files)}] ⏭️  Pulando: {video_file.name} (SRT já existe)")
            skipped += 1
            continue

        print(f"\n[{idx}/{len(video_files)}] 🎬 Transcrevendo: {video_file.name}")
        print(f"    💾 Saída: {output_file.name}")

        try:
            # Configurações BALANCEADAS entre qualidade e performance
            # Valores padrão do Whisper são otimizados, então mantemos a maioria
            # Apenas ajustamos o que não prejudica qualidade:
            #
            # fp16=False: Compatibilidade (não afeta qualidade, só velocidade em GPUs)
            # temperature=0: Mais consistente (sem randomização)
            # verbose=True: Mostra progresso frame-a-frame
            #
            # NÃO alteramos beam_size, best_of, patience pois afetam qualidade!

            result = model.transcribe(
                str(video_file.absolute()),
                language='pt',  # Português brasileiro
                verbose=True,
                task='transcribe',
                fp16=False,  # Compatibilidade com todos os processadores
                temperature=0.0  # Determinístico (mais consistente, não prejudica qualidade)
                # beam_size: mantém padrão (5) - afeta qualidade
                # best_of: mantém padrão (5) - afeta qualidade
                # patience: mantém padrão (1.0) - afeta qualidade
            )

            # Cria arquivo SRT
            create_srt(result['segments'], output_file)
            print(f"\n    ✅ Concluído: {output_file.name}")
            successful += 1

        except KeyboardInterrupt:
            print("\n\n⚠️  Processo interrompido pelo usuário.")
            raise
        except Exception as e:
            print(f"\n    ❌ Erro ao processar {video_file.name}: {e}")
            failed += 1
            continue

    # Resumo final
    print(f"\n{'='*60}")
    print(f"  RESUMO DA TRANSCRIÇÃO")
    print(f"{'='*60}")
    print(f"✅ Sucesso: {successful} arquivo(s)")
    if skipped > 0:
        print(f"⏭️  Pulados: {skipped} arquivo(s) (já existiam)")
    if failed > 0:
        print(f"❌ Falhas: {failed} arquivo(s)")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  TRANSCRITOR DE ÁUDIO/VÍDEO PARA SRT - WHISPER")
    print("  Otimizado para MacBook Air e computadores leves")
    print("="*60 + "\n")

    # Corrige certificados SSL (importante para Mac)
    fix_ssl_certificates()

    # Instala dependências se necessário
    install_dependencies()

    # Se passou argumento, usa como diretório
    directory = sys.argv[1] if len(sys.argv) > 1 else None

    try:
        transcribe_files(directory)
    except KeyboardInterrupt:
        print("\n\n⚠️  Processo interrompido pelo usuário.")
        print("💡 Você pode retomar a transcrição executando o script novamente.")
        print("   Arquivos já processados serão pulados automaticamente.\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
