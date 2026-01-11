import { Link } from 'react-router-dom';
import {
  Target,
  Camera,
  TrendingUp,
  Zap,
  ChevronRight,
  Check,
  MessageCircle,
  BookOpen,
  GraduationCap,
} from 'lucide-react';
import { ParticleBackground } from '../components/background/ParticleBackground';
import { Button, Card } from '../components/common';
import { Header } from '../components/layout/Header';
import { Footer } from '../components/layout/Footer';

// Feature data
const features = [
  {
    icon: Target,
    title: 'Mufredat Uyumu',
    description: 'MEB kazanimlariyla otomatik eslestirme. Her soru mufredattaki yerini bulur.',
  },
  {
    icon: Camera,
    title: 'Gorsel Analiz',
    description: 'Fotografladigin soruyu aninda coz. GPT-4o Vision ile gorsel anlama.',
  },
  {
    icon: TrendingUp,
    title: 'Kisisel Takip',
    description: 'Ogrenme ilerlemenizi izleyin. Eksik konulari ve kazanimlari kesfet.',
  },
  {
    icon: Zap,
    title: 'Anlik Cevaplar',
    description: 'GPT-5.2 destekli ogretmen aciklamalari. Adim adim cozum yollari.',
  },
];

// How it works steps
const steps = [
  {
    number: '01',
    title: 'Sorunuzu Girin',
    description: 'Sorunuzu yazin veya fotograflayin. Metin veya gorsel olarak gonderin.',
  },
  {
    number: '02',
    title: 'AI Analizi',
    description: 'Yapay zeka kazanimlari ve ders kitabi kaynaklarini bulur.',
  },
  {
    number: '03',
    title: 'Kisisel Aciklama',
    description: 'Seviyenize uygun, adim adim ogretmen aciklamasi alin.',
  },
];

// Pricing tiers
const pricingTiers = [
  {
    name: 'Ucretsiz',
    price: '0',
    period: 'TL',
    description: 'Baslamak icin ideal',
    features: ['10 soru/gun', 'Sadece metin', 'Temel dersler'],
    cta: 'Ucretsiz Basla',
    featured: false,
  },
  {
    name: 'Ogrenci',
    price: '29',
    period: 'TL/ay',
    description: 'Tam ogrenme deneyimi',
    features: ['Sinirsiz soru', 'Gorsel analiz', 'Tum dersler', 'Ilerleme takibi'],
    cta: 'Plani Sec',
    featured: true,
  },
  {
    name: 'Okul',
    price: 'Ozel',
    period: 'Fiyat',
    description: 'Kurumsal cozumler',
    features: ['Sinirsiz kullanici', 'Yonetim paneli', 'API erisimi', 'Ozel destek'],
    cta: 'Iletisime Gec',
    featured: false,
  },
];

// FAQ items
const faqItems = [
  {
    question: 'Hangi siniflari destekliyor?',
    answer: '9, 10, 11 ve 12. sinif mufredatlarini destekliyoruz. Tum MEB kazanimlari sistemimizde mevcut.',
  },
  {
    question: 'Gorsel sorular nasil calisiyor?',
    answer: 'Sorunuzun fotografini cekip yukleyin. GPT-4o Vision teknolojisi ile gorsel analiz yapilir ve sorunuz cozulur.',
  },
  {
    question: 'Verilerim guvenli mi?',
    answer: 'Evet, tum verileriniz sifrelenerek saklanir. KVKK uyumlu veri isleme politikalarimiz vardir.',
  },
  {
    question: 'Aboneligimi nasil iptal ederim?',
    answer: 'Ayarlar > Abonelik sayfasindan istediginiz zaman iptal edebilirsiniz. Iptal isleminden sonra donem sonuna kadar erisim devam eder.',
  },
];

const Landing = () => {
  return (
    <div className="min-h-screen bg-canvas relative overflow-hidden">
      {/* Background */}
      <ParticleBackground />

      {/* Header */}
      <Header />

      {/* Hero Section */}
      <section className="relative z-10 min-h-screen flex items-center justify-center px-4 pt-20">
        <div className="max-w-4xl mx-auto text-center animate-enter">
          {/* Glass Container */}
          <div className="glass-vellum p-12 md:p-16 rounded-3xl shadow-2xl">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-sepia/10 rounded-full mb-6">
              <GraduationCap className="w-4 h-4 text-sepia" />
              <span className="font-mono-custom text-[10px] text-sepia uppercase tracking-widest">
                Yapay Zeka Destekli Egitim
              </span>
            </div>

            <h1 className="heading-display mb-6">
              <span className="text-sepia">MEBA</span>
            </h1>

            <p className="text-lg md:text-xl text-neutral-600 font-light max-w-2xl mx-auto mb-8 leading-relaxed">
              MEB mufredatina uyumlu, kisisellestirilmis ogrenme deneyimi.
              Sorularinizi analiz eder, kazanimlari eslestirir, ders kitabi referanslari sunar.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link to="/kayit">
                <Button size="lg" rightIcon={<ChevronRight className="w-4 h-4" />}>
                  Ucretsiz Basla
                </Button>
              </Link>
              <Link to="/sohbet">
                <Button variant="secondary" size="lg" leftIcon={<MessageCircle className="w-4 h-4" />}>
                  Demo Dene
                </Button>
              </Link>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-6 mt-12 pt-8 border-t border-stone-200">
              <div>
                <p className="font-serif-custom text-3xl text-sepia">500+</p>
                <p className="label-mono mt-1">Kazanim</p>
              </div>
              <div>
                <p className="font-serif-custom text-3xl text-sepia">4</p>
                <p className="label-mono mt-1">Ders</p>
              </div>
              <div>
                <p className="font-serif-custom text-3xl text-sepia">9-12</p>
                <p className="label-mono mt-1">Sinif</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="relative z-10 py-24 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16 animate-enter">
            <h2 className="heading-section mb-4">Neden Meba?</h2>
            <p className="text-neutral-600 max-w-2xl mx-auto">
              Turk egitim sistemine ozel tasarlanmis, yapay zeka destekli ogrenme platformu.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((feature, index) => (
              <Card
                key={feature.title}
                variant="surface"
                hover
                className="animate-enter"
                style={{ animationDelay: `${index * 0.1}s` }}
              >
                <div className="w-12 h-12 rounded-xl bg-sepia/10 flex items-center justify-center mb-4">
                  <feature.icon className="w-6 h-6 text-sepia" />
                </div>
                <h3 className="font-serif-custom text-lg text-ink mb-2">{feature.title}</h3>
                <p className="text-sm text-neutral-600">{feature.description}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="relative z-10 py-24 px-4 bg-paper/50">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="heading-section mb-4">Nasil Calisiyor?</h2>
            <p className="text-neutral-600">Uc adimda ogrenmeye basla</p>
          </div>

          <div className="space-y-8">
            {steps.map((step, index) => (
              <div
                key={step.number}
                className="flex items-start gap-6 animate-enter"
                style={{ animationDelay: `${index * 0.15}s` }}
              >
                <div className="w-16 h-16 rounded-full card-surface flex items-center justify-center flex-shrink-0">
                  <span className="font-mono-custom text-lg text-sepia">{step.number}</span>
                </div>
                <div className="pt-3">
                  <h3 className="font-serif-custom text-xl text-ink mb-2">{step.title}</h3>
                  <p className="text-neutral-600">{step.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section className="relative z-10 py-24 px-4">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="heading-section mb-4">Fiyatlandirma</h2>
            <p className="text-neutral-600">Ihtiyacina uygun plani sec</p>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {pricingTiers.map((tier, index) => (
              <Card
                key={tier.name}
                variant={tier.featured ? 'elevated' : 'surface'}
                className={`animate-enter ${tier.featured ? 'ring-2 ring-sepia/20 scale-105' : ''}`}
                style={{ animationDelay: `${index * 0.1}s` }}
              >
                {tier.featured && (
                  <div className="text-center mb-4">
                    <span className="px-3 py-1 bg-sepia text-paper text-[10px] font-mono-custom uppercase tracking-widest rounded-full">
                      En Populer
                    </span>
                  </div>
                )}

                <div className="text-center mb-6">
                  <h3 className="font-serif-custom text-xl text-ink mb-2">{tier.name}</h3>
                  <div className="flex items-baseline justify-center gap-1">
                    <span className="font-serif-custom text-4xl text-sepia">{tier.price}</span>
                    <span className="text-neutral-500 text-sm">{tier.period}</span>
                  </div>
                  <p className="text-sm text-neutral-500 mt-2">{tier.description}</p>
                </div>

                <ul className="space-y-3 mb-6">
                  {tier.features.map((feature) => (
                    <li key={feature} className="flex items-center gap-2 text-sm text-neutral-600">
                      <Check className="w-4 h-4 text-sepia" />
                      {feature}
                    </li>
                  ))}
                </ul>

                <Link to={tier.name === 'Okul' ? '/iletisim' : '/kayit'}>
                  <Button
                    variant={tier.featured ? 'primary' : 'secondary'}
                    className="w-full"
                  >
                    {tier.cta}
                  </Button>
                </Link>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="relative z-10 py-24 px-4 bg-paper/50">
        <div className="max-w-3xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="heading-section mb-4">Sik Sorulan Sorular</h2>
          </div>

          <div className="space-y-4">
            {faqItems.map((item, index) => (
              <Card
                key={index}
                variant="surface"
                padding="lg"
                className="animate-enter"
                style={{ animationDelay: `${index * 0.1}s` }}
              >
                <h3 className="font-sans font-medium text-ink mb-2">{item.question}</h3>
                <p className="text-sm text-neutral-600">{item.answer}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="relative z-10 py-24 px-4">
        <div className="max-w-4xl mx-auto">
          <Card
            variant="glass"
            padding="lg"
            className="text-center bg-gradient-to-br from-sepia/5 to-accent/5"
          >
            <BookOpen className="w-12 h-12 text-sepia mx-auto mb-6" />
            <h2 className="heading-section mb-4 text-ink">Ogrenmeye Hemen Basla</h2>
            <p className="text-neutral-600 mb-8 max-w-xl mx-auto">
              Ucretsiz hesap olustur, ilk 10 sorunuzu hemen sor.
              Kredi karti gerektirmez.
            </p>
            <Link to="/kayit">
              <Button size="lg" rightIcon={<ChevronRight className="w-4 h-4" />}>
                Ucretsiz Kayit Ol
              </Button>
            </Link>
          </Card>
        </div>
      </section>

      {/* Footer */}
      <Footer />
    </div>
  );
};

export default Landing;
