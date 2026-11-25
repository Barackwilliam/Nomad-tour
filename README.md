# Nomad Explorer Tours — Website

Website ya kampuni ya utalii (safari, Kilimanjaro, Zanzibar, day trips) yenye **admin dashboard** ya kusimamia kila kitu.

- **Backend:** Django 5.2
- **Database:** PostgreSQL (Supabase)
- **Picha:** Supabase Storage (bucket ya umma) — kila picha inayopakiwa inabadilishwa kuwa WebP na kupunguzwa ukubwa ili site iwe na kasi
- **Dashboard:** Django admin + Unfold (`/admin/`)
- **Hosting:** Render (au hosting yoyote ya Python)

## Kilichomo

| Ukurasa | Anwani |
|---|---|
| Home (muundo wa seracadventure.com) | `/` |
| Kategoria (Kilimanjaro, Safari, Trekking, Zanzibar, Day trips, Climb + Safari) | `/kilimanjaro-climbing/` n.k. |
| Package moja (itinerary ya siku kwa siku, bei, booking form, WhatsApp) | `/kilimanjaro-climbing/7-days-kilimanjaro-climb-machame-route/` |
| Tours zote + filter (siku, bei, comfort, search) | `/tours/` |
| Group joining 2027 (Kilimanjaro + Safari, filter kwa mwezi, "Join group") | `/group-departures/` |
| Plan my trip / Contact / About / FAQ / Kurasa za taarifa | `/plan-your-trip/`, `/contact/`, `/about-us/`, `/faq/`, `/info/<slug>/` |
| SEO | `/sitemap.xml`, `/robots.txt`, JSON-LD (TravelAgency, TouristTrip, FAQ, Breadcrumbs, Events) |

**Data ya mwanzo** (`python manage.py seed_site`): packages 49 (44 kutoka nomadexplorertours.com pamoja na itinerary, bei na picha zake + 5 mpya), group departures 47 za 2027, FAQ 17 na kurasa 3 (Why book with us, Giving back, Booking terms).

Anwani za site ya zamani (`...php`) zinaelekezwa (301) kwenye kurasa mpya ili Google isipoteze nafasi.

## Kuendesha kwenye kompyuta (local)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # weka DEBUG=1, acha DATABASE_URL tupu => SQLite
python manage.py migrate
python manage.py seed_site     # packages, departures, picha
python manage.py createsuperuser
python manage.py runserver
```

Fungua http://localhost:8000 na dashboard http://localhost:8000/admin/

Majaribio: `python manage.py test tours`

## Kuweka hewani (Supabase + Render)

### 1. Supabase
1. Tengeneza project mpya.
2. **Database:** Connect → *Session pooler* → nakili connection string (port 5432). Hii ndiyo `DATABASE_URL`.
3. **Storage:** tengeneza bucket inayoitwa `nomad` na uiwekee **Public**.
4. Storage → Settings → **S3 access keys** → tengeneza key. Utapata `Access key ID`, `Secret` na `Region`.

### 2. Render
1. New → **Blueprint** → chagua repo hii (inasoma `render.yaml`).
2. Jaza vigezo:
   - `DATABASE_URL`, `SUPABASE_URL` (mfano `https://xxxx.supabase.co`), `SUPABASE_S3_ACCESS_KEY_ID`, `SUPABASE_S3_SECRET_ACCESS_KEY`, `SUPABASE_S3_REGION`
   - `ALLOWED_HOSTS=nomadexplorertours.com,www.nomadexplorertours.com`
   - `CSRF_TRUSTED_ORIGINS=https://nomadexplorertours.com,https://www.nomadexplorertours.com`
   - `SITE_URL=https://www.nomadexplorertours.com`
   - `DJANGO_SUPERUSER_USERNAME` na `DJANGO_SUPERUSER_PASSWORD` (msimamizi wa kwanza)
3. Deploy. `build.sh` inafanya migrate, inatengeneza msimamizi na kupakia data ya mwanzo + picha kwenye Supabase **mara ya kwanza tu** (database ikiwa tupu).

### 3. Domain
Render → Settings → Custom domains → ongeza domain ya mteja, kisha weka DNS (CNAME/A) kwenye alipoinunua domain.

### 4. Baada ya kuwa hewani
- Google Search Console: ongeza site, weka `google_site_verification` kwenye *Site settings*, kisha tuma `https://www.../sitemap.xml`.
- Weka Google Analytics ID (G-XXXX) kwenye *Site settings → SEO & analytics*.
- (Hiari) Weka `EMAIL_HOST...` ili mteja apate email kila enquiry mpya inapoingia.

## Mteja anasimamia nini kwenye dashboard

- **Enquiries & bookings** — kila form ya site inaingia hapa (na email kama imewekwa). Kitufe cha kumjibu kwa WhatsApp/Email, status (New / Replied / Booked).
- **Tour packages** — kuongeza/kubadilisha package, picha, itinerary ya kila siku, bei kwa idadi ya watu, kuonyesha kwenye home page, SEO title/description. Kitendo cha *Duplicate* kunakili package.
- **Group departures** — tarehe, bei, nafasi (booked / total), status (Open, Guaranteed, Full). Mwaka unaoonyeshwa unabadilishwa kwenye *Site settings → Group departures*.
- **Site settings** — logo, simu, WhatsApp, email, anwani, social media, picha za home page, maandishi ya About, Google Analytics.
- **Categories, Pages & guides, FAQs, Reviews.**

## Kasi (speed)

Lighthouse (simu, production mode): **98–100** kwenye Performance, Accessibility, Best practices na SEO kwa kurasa zote kuu. Home page LCP ≈ 0.9s.

Kinachoifanya iwe fast:
- Kila picha inayopakiwa inabadilishwa kuwa WebP na nakala ndogo (480/800/1200px) zinatengenezwa; simu inapakua picha ndogo tu (`srcset`). Kwa picha zilizopo tayari: `python manage.py make_image_variants`.
- Fonts ziko kwenye site yenyewe (hakuna Google Fonts), zina `preload`.
- Data ya kurasa inakaa kwenye cache; ukibadilisha chochote kwenye dashboard cache inajisafisha papo hapo.
- Kurasa zinapakiwa kabla mtu hajabonyeza link (Speculation Rules: prerender ukipeleka mouse), na kuna mpito laini kati ya kurasa (View Transitions).
- Static files zinabanwa (Brotli/gzip) na kukaa kwenye cache ya browser kwa mwaka mmoja.

## Muundo wa code

```
config/            settings, urls
tours/models.py    Tour, TourDay, TourPrice, GroupDeparture, Enquiry, Category, Page, FAQ, Testimonial, SiteSettings
tours/admin.py     dashboard (Unfold)
tours/views.py     kurasa zote + forms
tours/seo.py       JSON-LD (structured data)
tours/images.py    kupunguza picha, WebP na nakala ndogo za simu
tours/cache.py     cache ya data ya kurasa
tours/seasons.py   'When to go' (mwezi kwa mwezi)
tours/seed/        data.json + picha za mwanzo
tours/templates/   HTML
tours/static/      CSS, JS, logo
```
