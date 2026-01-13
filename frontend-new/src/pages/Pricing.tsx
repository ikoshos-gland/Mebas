import { Link } from 'react-router-dom';
import { Check, X, ChevronRight, Building2, GraduationCap, Sparkles } from 'lucide-react';
import { ParticleBackground } from '../components/background/ParticleBackground';
import { Header } from '../components/layout/Header';
import { Footer } from '../components/layout/Footer';
import { Card, Button } from '../components/common';

const plans = [
  {
    id: 'free',
    name: 'Ücretsiz',
    price: '0',
    period: '',
    description: 'Başlamak için ideal',
    icon: Sparkles,
    features: [
      { text: '10 soru/gün', included: true },
      { text: 'Metin tabanlı sorular', included: true },
      { text: 'Temel dersler', included: true },
      { text: 'Görsel analiz', included: false },
      { text: 'İlerleme takibi', included: false },
      { text: 'Öncelikli destek', included: false },
    ],
    cta: 'Ücretsiz Başla',
    featured: false,
  },
  {
    id: 'student',
    name: 'Öğrenci',
    price: '29',
    period: '/ay',
    description: 'Tam öğrenme deneyimi',
    icon: GraduationCap,
    features: [
      { text: 'Sınırsız soru', included: true },
      { text: 'Görsel analiz (GPT-4o Vision)', included: true },
      { text: 'Tüm dersler', included: true },
      { text: 'Kişisel ilerleme takibi', included: true },
      { text: 'Çalışma önerileri', included: true },
      { text: 'E-posta desteği', included: true },
    ],
    cta: 'Planı Seç',
    featured: true,
  },
  {
    id: 'school',
    name: 'Okul',
    price: 'Özel',
    period: 'fiyat',
    description: 'Kurumsal çözümler',
    icon: Building2,
    features: [
      { text: 'Sınırsız kullanıcı', included: true },
      { text: 'Yönetim paneli', included: true },
      { text: 'Öğrenci/sınıf analitikleri', included: true },
      { text: 'API erişimi', included: true },
      { text: 'Özel entegrasyonlar', included: true },
      { text: 'Öncelikli destek', included: true },
    ],
    cta: 'İletişime Geç',
    featured: false,
  },
];

const faqItems = [
  {
    question: 'Aboneliğimi istediğim zaman iptal edebilir miyim?',
    answer: 'Evet, aboneliğinizi istediğiniz zaman iptal edebilirsiniz. İptal ettikten sonra mevcut dönem sonuna kadar erişiminiz devam eder.',
  },
  {
    question: 'Ödeme yöntemleri nelerdir?',
    answer: 'Kredi kartı ve banka kartı ile ödeme yapabilirsiniz. Tüm ödemeler güvenli altyapımız üzerinden gerçekleştirilir.',
  },
  {
    question: 'Okul planı için nasıl başvurabilirim?',
    answer: 'Okul planı için bizimle iletişime geçin. Okulunuzun ihtiyaçlarına göre özel bir fiyat teklifi hazırlayacağız.',
  },
  {
    question: 'Ücretsiz deneme süresi var mı?',
    answer: 'Ücretsiz plan ile hemen başlayabilirsiniz. Günde 10 soru sorarak platformu deneyebilirsiniz.',
  },
];

const Pricing = () => {
  return (
    <div className="min-h-screen bg-canvas relative">
      <ParticleBackground opacity={0.4} />
      <Header />

      <main className="relative z-10 pt-32 pb-24 px-4">
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <div className="text-center mb-16 animate-enter">
            <h1 className="heading-display mb-4">Fiyatlandırma</h1>
            <p className="text-lg text-neutral-600 max-w-2xl mx-auto">
              İhtiyacınıza uygun planı seçin. Tüm planlarda MEB müfredatına uyumlu yapay zeka destekli eğitim.
            </p>
          </div>

          {/* Pricing Cards */}
          <div className="grid md:grid-cols-3 gap-6 mb-24">
            {plans.map((plan, index) => (
              <Card
                key={plan.id}
                variant={plan.featured ? 'elevated' : 'surface'}
                padding="none"
                className={`
                  animate-enter overflow-hidden
                  ${plan.featured ? 'ring-2 ring-sepia/30 scale-105 z-10' : ''}
                `}
                style={{ animationDelay: `${index * 0.1}s` }}
              >
                {plan.featured && (
                  <div className="bg-sepia text-paper text-center py-2">
                    <span className="font-mono-custom text-[10px] uppercase tracking-widest">
                      En Popüler
                    </span>
                  </div>
                )}

                <div className="p-8">
                  {/* Plan Header */}
                  <div className="text-center mb-8">
                    <div
                      className={`
                        w-14 h-14 rounded-2xl mx-auto mb-4 flex items-center justify-center
                        ${plan.featured ? 'bg-sepia/10' : 'bg-stone-100'}
                      `}
                    >
                      <plan.icon
                        className={`w-7 h-7 ${plan.featured ? 'text-sepia' : 'text-neutral-500'}`}
                      />
                    </div>

                    <h2 className="font-serif-custom text-2xl text-ink mb-2">{plan.name}</h2>

                    <div className="flex items-baseline justify-center gap-1 mb-2">
                      <span className="font-serif-custom text-4xl text-sepia">
                        {plan.price === 'Özel' ? '' : plan.price}
                        {plan.price !== 'Özel' && <span className="text-lg">TL</span>}
                        {plan.price === 'Özel' && plan.price}
                      </span>
                      {plan.period && (
                        <span className="text-neutral-500 text-sm">{plan.period}</span>
                      )}
                    </div>

                    <p className="text-sm text-neutral-500">{plan.description}</p>
                  </div>

                  {/* Features */}
                  <ul className="space-y-3 mb-8">
                    {plan.features.map((feature, i) => (
                      <li key={i} className="flex items-center gap-3">
                        {feature.included ? (
                          <div className="w-5 h-5 rounded-full bg-green-100 flex items-center justify-center">
                            <Check className="w-3 h-3 text-green-600" />
                          </div>
                        ) : (
                          <div className="w-5 h-5 rounded-full bg-stone-100 flex items-center justify-center">
                            <X className="w-3 h-3 text-neutral-400" />
                          </div>
                        )}
                        <span
                          className={`text-sm ${
                            feature.included ? 'text-ink' : 'text-neutral-400'
                          }`}
                        >
                          {feature.text}
                        </span>
                      </li>
                    ))}
                  </ul>

                  {/* CTA */}
                  <Link to={plan.id === 'school' ? '/iletisim' : '/kayit'}>
                    <Button
                      variant={plan.featured ? 'primary' : 'secondary'}
                      className="w-full"
                      rightIcon={<ChevronRight className="w-4 h-4" />}
                    >
                      {plan.cta}
                    </Button>
                  </Link>
                </div>
              </Card>
            ))}
          </div>

          {/* Comparison Table (Desktop) */}
          <div className="hidden lg:block mb-24">
            <h2 className="heading-section text-center mb-8">Detaylı Karşılaştırma</h2>

            <Card variant="surface" padding="none" className="overflow-hidden animate-enter">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-stone-200">
                    <th className="text-left p-6 font-sans font-medium text-ink">Özellik</th>
                    <th className="text-center p-6 font-sans font-medium text-ink">Ücretsiz</th>
                    <th className="text-center p-6 font-sans font-medium text-sepia bg-sepia/5">
                      Öğrenci
                    </th>
                    <th className="text-center p-6 font-sans font-medium text-ink">Okul</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    ['Günlük soru limiti', '10', 'Sınırsız', 'Sınırsız'],
                    ['Görsel analiz', false, true, true],
                    ['Ders sayısı', '2', 'Tümü', 'Tümü'],
                    ['İlerleme takibi', false, true, true],
                    ['Çalışma önerileri', false, true, true],
                    ['Yönetim paneli', false, false, true],
                    ['API erişimi', false, false, true],
                    ['Öncelikli destek', false, false, true],
                  ].map(([feature, free, student, school], i) => (
                    <tr key={i} className="border-b border-stone-100 last:border-none">
                      <td className="p-6 text-sm text-neutral-600">{feature}</td>
                      <td className="p-6 text-center">
                        {typeof free === 'boolean' ? (
                          free ? (
                            <Check className="w-5 h-5 text-green-500 mx-auto" />
                          ) : (
                            <X className="w-5 h-5 text-neutral-300 mx-auto" />
                          )
                        ) : (
                          <span className="text-sm text-ink">{free}</span>
                        )}
                      </td>
                      <td className="p-6 text-center bg-sepia/5">
                        {typeof student === 'boolean' ? (
                          student ? (
                            <Check className="w-5 h-5 text-green-500 mx-auto" />
                          ) : (
                            <X className="w-5 h-5 text-neutral-300 mx-auto" />
                          )
                        ) : (
                          <span className="text-sm text-ink font-medium">{student}</span>
                        )}
                      </td>
                      <td className="p-6 text-center">
                        {typeof school === 'boolean' ? (
                          school ? (
                            <Check className="w-5 h-5 text-green-500 mx-auto" />
                          ) : (
                            <X className="w-5 h-5 text-neutral-300 mx-auto" />
                          )
                        ) : (
                          <span className="text-sm text-ink">{school}</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          </div>

          {/* FAQ */}
          <div className="max-w-3xl mx-auto">
            <h2 className="heading-section text-center mb-8">Sıkça Sorulan Sorular</h2>

            <div className="space-y-4">
              {faqItems.map((item, index) => (
                <Card
                  key={index}
                  variant="surface"
                  className="animate-enter"
                  style={{ animationDelay: `${index * 0.1}s` }}
                >
                  <h3 className="font-sans font-medium text-ink mb-2">{item.question}</h3>
                  <p className="text-sm text-neutral-600">{item.answer}</p>
                </Card>
              ))}
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default Pricing;
