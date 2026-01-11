import { Link } from 'react-router-dom';
import { Mail, Twitter, Linkedin, Github } from 'lucide-react';

export const Footer = () => {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="relative z-10 bg-ink text-paper/80">
      <div className="max-w-7xl mx-auto px-4 md:px-8 py-16">
        <div className="grid md:grid-cols-4 gap-12 mb-12">
          {/* Brand */}
          <div className="md:col-span-1">
            <Link to="/" className="flex items-center gap-3 mb-4">
              <div className="w-8 h-8 border border-paper/20 flex items-center justify-center rounded relative overflow-hidden">
                <div className="absolute w-full h-[0.5px] bg-paper rotate-45" />
                <div className="absolute w-full h-[0.5px] bg-paper -rotate-45" />
              </div>
              <span className="font-serif-custom text-xl text-paper">Meba</span>
            </Link>
            <p className="text-sm text-paper/60 mb-4">
              MEB mufredatina uyumlu, yapay zeka destekli egitim platformu.
            </p>
            <div className="flex items-center gap-3">
              <a href="#" className="p-2 hover:bg-paper/10 rounded-lg transition-colors">
                <Twitter className="w-4 h-4" />
              </a>
              <a href="#" className="p-2 hover:bg-paper/10 rounded-lg transition-colors">
                <Linkedin className="w-4 h-4" />
              </a>
              <a href="#" className="p-2 hover:bg-paper/10 rounded-lg transition-colors">
                <Github className="w-4 h-4" />
              </a>
              <a href="mailto:destek@meba.edu.tr" className="p-2 hover:bg-paper/10 rounded-lg transition-colors">
                <Mail className="w-4 h-4" />
              </a>
            </div>
          </div>

          {/* Product Links */}
          <div>
            <h3 className="font-mono-custom text-[10px] uppercase tracking-widest text-paper/40 mb-4">
              Urun
            </h3>
            <ul className="space-y-2">
              <li>
                <Link to="/sohbet" className="text-sm hover:text-paper transition-colors">
                  Sohbet
                </Link>
              </li>
              <li>
                <Link to="/fiyatlar" className="text-sm hover:text-paper transition-colors">
                  Fiyatlar
                </Link>
              </li>
              <li>
                <a href="#features" className="text-sm hover:text-paper transition-colors">
                  Ozellikler
                </a>
              </li>
              <li>
                <a href="#" className="text-sm hover:text-paper transition-colors">
                  API
                </a>
              </li>
            </ul>
          </div>

          {/* Support Links */}
          <div>
            <h3 className="font-mono-custom text-[10px] uppercase tracking-widest text-paper/40 mb-4">
              Destek
            </h3>
            <ul className="space-y-2">
              <li>
                <a href="#faq" className="text-sm hover:text-paper transition-colors">
                  SSS
                </a>
              </li>
              <li>
                <a href="mailto:destek@meba.edu.tr" className="text-sm hover:text-paper transition-colors">
                  Iletisim
                </a>
              </li>
              <li>
                <a href="#" className="text-sm hover:text-paper transition-colors">
                  Dokumantasyon
                </a>
              </li>
            </ul>
          </div>

          {/* Legal Links */}
          <div>
            <h3 className="font-mono-custom text-[10px] uppercase tracking-widest text-paper/40 mb-4">
              Yasal
            </h3>
            <ul className="space-y-2">
              <li>
                <a href="#" className="text-sm hover:text-paper transition-colors">
                  Gizlilik Politikasi
                </a>
              </li>
              <li>
                <a href="#" className="text-sm hover:text-paper transition-colors">
                  Kullanim Kosullari
                </a>
              </li>
              <li>
                <a href="#" className="text-sm hover:text-paper transition-colors">
                  KVKK Aydinlatma
                </a>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="pt-8 border-t border-paper/10 flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="text-xs text-paper/40">
            &copy; {currentYear} Meba. Tum haklari saklidir.
          </p>
          <p className="text-xs text-paper/40">
            <span className="font-mono-custom">GPT-5.2</span> ve{' '}
            <span className="font-mono-custom">Azure AI Search</span> ile guclendirilmistir.
          </p>
        </div>
      </div>
    </footer>
  );
};
