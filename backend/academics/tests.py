from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import AdminUser
from academics.models import (
    AcademicDocument, Chapter, DocumentQuestion, Programme, SchoolClass, Subject, TeachingSlot,
)


def json_client(user=None):
    """A test client that posts JSON, which the nested question lists require."""
    client = APIClient()
    client.default_format = 'json'
    if user is not None:
        client.force_authenticate(user)
    return client


class DocumentTestBase(TestCase):
    """One programme, one subject and one chapter to hang documents off."""

    def setUp(self):
        self.admin = AdminUser.objects.create_user(
            username='tester', password='pw-for-tests-123', role='admin', is_staff=True
        )
        self.client = json_client(self.admin)
        self.programme = Programme.objects.create(name='Class 10', level='Secondary', duration='2 years')
        self.subject = Subject.objects.create(programme=self.programme, name='Mathematics', code='MATH')
        self.chapter = Chapter.objects.create(subject=self.subject, name='Chapter 1 - Real Numbers')

    def make_document(self, **overrides):
        """A question document that passes validation, so a test can vary one field."""
        payload = {
            'title': 'Chapter 1 - Exercise',
            'programme': self.programme.id,
            'subject': self.subject.id,
            'chapter': self.chapter.id,
            'document_type': 'questions',
            'questions': [
                {'question_type': 'short_answer', 'question': 'Define a prime number.', 'answer': 'Only divisible by 1 and itself.'},
            ],
        }
        payload.update(overrides)
        return payload


class ChapterApiTests(DocumentTestBase):
    """A chapter always hangs off a subject, so the subject drives the list."""

    def test_chapter_is_listed_under_its_own_subject_only(self):
        other = Subject.objects.create(programme=self.programme, name='Science', code='SCI')
        Chapter.objects.create(subject=other, name='Chapter 1 - Physics')

        response = self.client.get(reverse('chapter-list'), {'subject': self.subject.id})

        self.assertEqual(response.status_code, 200)
        self.assertEqual([c['id'] for c in response.data['results']], [self.chapter.id])

    def test_chapter_name_is_unique_within_a_subject(self):
        response = self.client.post(reverse('chapter-list'), {
            'subject': self.subject.id, 'name': self.chapter.name,
        })

        self.assertEqual(response.status_code, 400)

    def test_same_chapter_name_allowed_under_a_different_subject(self):
        other = Subject.objects.create(programme=self.programme, name='Science', code='SCI')

        response = self.client.post(reverse('chapter-list'), {
            'subject': other.id, 'name': self.chapter.name,
        })

        self.assertEqual(response.status_code, 201)

    def test_anyone_may_read_but_only_an_admin_may_add(self):
        anonymous = json_client()

        self.assertEqual(anonymous.get(reverse('chapter-list')).status_code, 200)
        self.assertEqual(
            anonymous.post(reverse('chapter-list'), {'subject': self.subject.id, 'name': 'Nope'}).status_code,
            401,
        )

    def test_a_teacher_token_cannot_add_a_chapter(self):
        """Reading is public, so a signed-in teacher is the case worth guarding."""
        teacher = AdminUser.objects.create_user(username='teacher', password='pw-for-tests-123', role='teacher')
        self.client.force_authenticate(teacher)

        response = self.client.post(reverse('chapter-list'), {'subject': self.subject.id, 'name': 'Nope'})

        self.assertEqual(response.status_code, 403)


class DocumentQuestionTests(DocumentTestBase):
    """Questions are written nested, so one request saves a document and its questions."""

    def test_questions_save_nested_and_in_the_order_listed(self):
        response = self.client.post(reverse('academic-doc-list'), self.make_document(questions=[
            {'question_type': 'short_answer', 'question': 'First', 'order': 2},
            {'question_type': 'short_answer', 'question': 'Second', 'order': 1},
            {'question_type': 'short_answer', 'question': 'Third', 'order': 3},
        ]))

        self.assertEqual(response.status_code, 201)
        saved = list(AcademicDocument.objects.get().questions.order_by('order'))
        # The list the form sent is what gets saved, so the sequence the admin
        # arranged on screen is the sequence that comes back.
        self.assertEqual([q.question for q in saved], ['First', 'Second', 'Third'])
        self.assertEqual([q.order for q in saved], [0, 1, 2])

    def test_an_order_sent_by_the_client_does_not_break_the_save(self):
        """A client may send `order`; it must not be passed to the model twice."""
        response = self.client.post(reverse('academic-doc-list'), self.make_document(questions=[
            {'question_type': 'short_answer', 'question': 'Only question', 'order': 9},
        ]))

        self.assertEqual(response.status_code, 201)
        self.assertEqual(AcademicDocument.objects.get().questions.get().order, 0)

    def test_multiple_choice_keeps_its_options_and_the_right_answer(self):
        response = self.client.post(reverse('academic-doc-list'), self.make_document(questions=[
            {'question_type': 'multiple_choice', 'question': 'Which is prime?', 'options': ['3', '4', '5', '6'], 'correct_option': 'c'},
        ]))

        self.assertEqual(response.status_code, 201)
        saved = DocumentQuestion.objects.get()
        self.assertEqual(saved.options, ['3', '4', '5', '6'])
        # Lower case in the form, stored upper case so it always matches the A-D labels.
        self.assertEqual(saved.correct_option, 'C')

    def test_a_question_left_half_filled_is_turned_away(self):
        """The form always shows four boxes, so a gap means the admin is not finished."""
        response = self.client.post(reverse('academic-doc-list'), self.make_document(questions=[
            {'question_type': 'multiple_choice', 'question': 'Which is prime?', 'options': ['3', '4', '', ''], 'correct_option': 'A'},
        ]))

        self.assertEqual(response.status_code, 400)
        self.assertIn('options', str(response.data))

    def test_retyping_a_question_drops_the_options_it_no_longer_needs(self):
        """Changing type in the form must not leave a stale answer letter behind."""
        self.client.post(reverse('academic-doc-list'), self.make_document(questions=[
            {'question_type': 'multiple_choice', 'question': 'Which is prime?', 'options': ['3', '4', '5', '6'], 'correct_option': 'C'},
        ]))
        document = AcademicDocument.objects.get()

        response = self.client.patch(
            reverse('academic-doc-detail', args=[document.id]),
            {'questions': [{'question_type': 'true_false', 'question': 'Which is prime?', 'answer': 'True'}]},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        saved = DocumentQuestion.objects.get()
        self.assertEqual((saved.question_type, saved.options, saved.correct_option), ('true_false', [], ''))
        self.assertEqual(saved.answer, 'True')

    def test_saving_a_document_again_replaces_its_questions_rather_than_adding_to_them(self):
        self.client.post(reverse('academic-doc-list'), self.make_document(questions=[
            {'question_type': 'short_answer', 'question': 'One'},
            {'question_type': 'short_answer', 'question': 'Two'},
        ]))
        document = AcademicDocument.objects.get()

        self.client.patch(
            reverse('academic-doc-detail', args=[document.id]),
            {'questions': [{'question_type': 'short_answer', 'question': 'Only one now'}]},
            format='json',
        )

        self.assertEqual(document.questions.count(), 1)
        self.assertEqual(document.questions.get().question, 'Only one now')

    def test_multiple_choice_needs_all_four_options_and_a_correct_one(self):
        for questions in (
            [{'question_type': 'multiple_choice', 'question': 'Q?', 'options': ['a', 'b'], 'correct_option': 'A'}],
            [{'question_type': 'multiple_choice', 'question': 'Q?', 'options': ['a', 'b', 'c', 'd']}],
        ):
            with self.subTest(questions=questions):
                response = self.client.post(reverse('academic-doc-list'), self.make_document(questions=questions))
                self.assertEqual(response.status_code, 400)
                self.assertFalse(AcademicDocument.objects.exists())


class DocumentValidationTests(DocumentTestBase):
    """The form's rules, enforced on the server so the API cannot skip them."""

    def test_a_question_document_needs_a_question(self):
        response = self.client.post(reverse('academic-doc-list'), self.make_document(document_type='qa', questions=[]))

        self.assertEqual(response.status_code, 400)
        self.assertIn('questions', response.data)

    def test_a_file_document_needs_a_file(self):
        response = self.client.post(reverse('academic-doc-list'), self.make_document(
            document_type='study_material', questions=[], file_url='',
        ))

        self.assertEqual(response.status_code, 400)
        self.assertIn('file_url', response.data)

    def test_a_question_document_needs_no_file(self):
        response = self.client.post(reverse('academic-doc-list'), self.make_document(file_url=''))

        self.assertEqual(response.status_code, 201)
        self.assertEqual(AcademicDocument.objects.get().file_url, '')

    def test_the_chapter_must_belong_to_the_chosen_subject(self):
        other = Subject.objects.create(programme=self.programme, name='Science', code='SCI')

        response = self.client.post(reverse('academic-doc-list'), self.make_document(subject=other.id))

        self.assertEqual(response.status_code, 400)
        self.assertIn('chapter', response.data)

    def test_the_subject_must_belong_to_the_chosen_programme(self):
        other = Programme.objects.create(name='Class 12', level='Senior Secondary', duration='2 years')

        response = self.client.post(reverse('academic-doc-list'), self.make_document(programme=other.id))

        self.assertEqual(response.status_code, 400)
        self.assertIn('subject', response.data)

    def test_a_new_document_starts_as_a_draft(self):
        self.client.post(reverse('academic-doc-list'), self.make_document())

        self.assertEqual(AcademicDocument.objects.get().status, 'draft')

    def test_naming_fields_come_back_filled_in(self):
        response = self.client.post(reverse('academic-doc-list'), self.make_document())

        self.assertEqual(response.data['programme_name'], self.programme.name)
        self.assertEqual(response.data['subject_name'], self.subject.name)
        self.assertEqual(response.data['chapter_name'], self.chapter.name)
        self.assertEqual(response.data['question_count'], 1)


class DocumentDuplicateSaveTests(DocumentTestBase):
    """
    A double-clicked Save, or a retried request after a dropped connection,
    must not leave two documents behind.
    """

    def test_the_same_client_token_saves_one_document(self):
        payload = self.make_document(client_token='form-token-1')

        first = self.client.post(reverse('academic-doc-list'), payload)
        second = self.client.post(reverse('academic-doc-list'), payload)

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(first.data['id'], second.data['id'])
        self.assertEqual(AcademicDocument.objects.count(), 1)

    def test_a_repeated_save_returns_the_document_as_it_was_first_saved(self):
        """The retry is ignored rather than applied twice."""
        self.client.post(reverse('academic-doc-list'), self.make_document(client_token='form-token-1'))
        retry = self.make_document(title='Typed again by mistake', client_token='form-token-1')

        response = self.client.post(reverse('academic-doc-list'), retry)

        self.assertEqual(response.data['title'], 'Chapter 1 - Exercise')
        self.assertEqual(AcademicDocument.objects.get().title, 'Chapter 1 - Exercise')

    def test_the_saved_document_is_not_blanked_by_a_repeat_without_questions(self):
        """A repeat that somehow lost its questions still must not overwrite the good row."""
        self.client.post(reverse('academic-doc-list'), self.make_document(client_token='form-token-1'))

        response = self.client.post(reverse('academic-doc-list'), self.make_document(client_token='form-token-1', questions=[]))

        self.assertEqual(response.status_code, 201)
        self.assertEqual(AcademicDocument.objects.get().questions.count(), 1)

    def test_documents_without_a_token_are_all_kept(self):
        """Nothing else in the site sends a token, so it must stay optional."""
        for title in ('First', 'Second'):
            response = self.client.post(reverse('academic-doc-list'), self.make_document(title=title))

            self.assertEqual(response.status_code, 201)

        self.assertEqual(AcademicDocument.objects.count(), 2)


class DocumentVisibilityTests(DocumentTestBase):
    """A draft is an admin's working copy; the public site only sees published work."""

    def setUp(self):
        super().setUp()
        self.draft = self.client.post(reverse('academic-doc-list'), self.make_document(title='Draft set')).data['id']
        self.published = self.client.post(
            reverse('academic-doc-list'), self.make_document(title='Published set', status='published')
        ).data['id']

    def test_an_admin_sees_drafts_and_published_documents_together(self):
        response = self.client.get(reverse('academic-doc-list'))

        self.assertEqual(response.data['count'], 2)

    def test_the_public_list_leaves_drafts_out(self):
        anonymous = json_client()

        response = anonymous.get(reverse('academic-doc-list'), {'published': 'true'})

        self.assertEqual([d['id'] for d in response.data['results']], [self.published])

    def test_the_public_cannot_write_a_document(self):
        anonymous = json_client()

        response = anonymous.post(reverse('academic-doc-list'), self.make_document())

        self.assertEqual(response.status_code, 401)
        self.assertEqual(AcademicDocument.objects.count(), 2)


class DatedPeriodTests(TestCase):
    """
    A period is weekly by default, and dated only when a single day is named,
    for the lessons the weekly grid cannot hold: an extra class, a swapped
    period, one session in the lab.
    """

    # 2026-10-09 is a Friday, which the tests below lean on.
    FRIDAY = '2026-10-09'
    NEXT_FRIDAY = '2026-10-16'

    def setUp(self):
        self.client = json_client(
            AdminUser.objects.create_user(username='boss', password='pw-for-tests-123', role='admin', is_staff=True)
        )
        self.teacher = AdminUser.objects.create_user(username='teacher1', password='pw-for-tests-123', role='teacher')
        self.other_teacher = AdminUser.objects.create_user(username='teacher2', password='pw-for-tests-123', role='teacher')
        programme = Programme.objects.create(name='Class 10', level='Secondary', duration='2 years')
        self.school_class = SchoolClass.objects.create(name='Class 10', programme=programme)
        self.other_class = SchoolClass.objects.create(name='Class 9', programme=programme)
        subject = Subject.objects.create(programme=programme, name='Mathematics', code='MATH')
        self.subject = subject

    def weekly(self, day=4, start='09:45', teacher=None, school_class=None, **extra):
        """A normal repeating period, the way the timetable has always worked."""
        hour, minute = (int(part) for part in start.split(':'))
        end = extra.pop('end_time', f'{hour + 1:02d}:{minute:02d}')
        payload = {
            'teacher': (teacher or self.teacher).id,
            'school_class': (school_class or self.school_class).id,
            'subject': self.subject.id,
            'day_of_week': day,
            'start_time': start,
            'end_time': end,
            'room': '101',
        }
        payload.update(extra)
        return payload

    def dated(self, date, start='09:45', teacher=None, **extra):
        """A single lesson on one calendar day."""
        payload = self.weekly(start=start, teacher=teacher, date=date)
        payload.update(extra)
        return payload

    def test_a_period_with_no_date_stays_weekly(self):
        response = self.client.post(reverse('teaching-slot-list'), self.weekly())

        self.assertEqual(response.status_code, 201)
        slot = TeachingSlot.objects.get()
        self.assertIsNone(slot.date)
        self.assertEqual(slot.day_of_week, 4)
        self.assertFalse(slot.is_one_off)

    def test_a_dated_period_takes_its_weekday_from_the_date(self):
        """The day is worked out, so a dated period can never be filed under a
        weekday that the date disagrees with."""
        # 2026-10-12 is a Monday; asking for Friday alongside it must not stick.
        response = self.client.post(reverse('teaching-slot-list'), self.dated('2026-10-12', day_of_week=4))

        self.assertEqual(response.status_code, 201)
        slot = TeachingSlot.objects.get()
        self.assertEqual(str(slot.date), '2026-10-12')
        self.assertEqual(slot.day_of_week, 0)
        self.assertTrue(slot.is_one_off)

    def test_the_same_class_twice_in_one_day_is_fine_at_different_times(self):
        first = self.client.post(reverse('teaching-slot-list'), self.weekly(start='09:45'))
        second = self.client.post(reverse('teaching-slot-list'), self.weekly(start='10:50'))

        self.assertEqual((first.status_code, second.status_code), (201, 201))
        self.assertEqual(TeachingSlot.objects.count(), 2)

    def test_a_teacher_cannot_start_two_periods_at_the_same_time(self):
        self.client.post(reverse('teaching-slot-list'), self.weekly(start='09:45'))

        response = self.client.post(reverse('teaching-slot-list'), self.weekly(start='09:45', school_class=self.other_class))

        self.assertEqual(response.status_code, 400)
        self.assertIn('already has a period', str(response.data).lower())

    def test_a_teacher_cannot_start_two_periods_at_the_same_time_on_the_same_date(self):
        self.client.post(reverse('teaching-slot-list'), self.dated(self.FRIDAY, start='09:45'))

        response = self.client.post(reverse('teaching-slot-list'), self.dated(self.FRIDAY, start='09:45'))

        self.assertEqual(response.status_code, 400)
        self.assertIn(self.FRIDAY[8:10], str(response.data))

    def test_the_same_time_on_a_different_date_is_allowed(self):
        """Two Fridays in a month can each hold the extra lesson."""
        first = self.client.post(reverse('teaching-slot-list'), self.dated(self.FRIDAY, start='09:45'))
        second = self.client.post(reverse('teaching-slot-list'), self.dated(self.NEXT_FRIDAY, start='09:45'))

        self.assertEqual((first.status_code, second.status_code), (201, 201))
        self.assertEqual(TeachingSlot.objects.count(), 2)

    def test_a_dated_lesson_is_refused_where_the_teacher_is_already_booked_that_day(self):
        """The weekly period does run on that Friday, so the extra one collides."""
        self.client.post(reverse('teaching-slot-list'), self.weekly(start='09:45'))

        response = self.client.post(reverse('teaching-slot-list'), self.dated(self.FRIDAY, start='09:45'))

        self.assertEqual(response.status_code, 400)
        self.assertIn('Mathematics', str(response.data))

    def test_a_dated_lesson_is_fine_at_a_time_the_teacher_is_free(self):
        self.client.post(reverse('teaching-slot-list'), self.weekly(start='09:45'))

        response = self.client.post(reverse('teaching-slot-list'), self.dated(self.FRIDAY, start='14:00', end_time='15:00'))

        self.assertEqual(response.status_code, 201)

    def test_two_teachers_can_teach_at_the_same_time_on_the_same_date(self):
        first = self.client.post(reverse('teaching-slot-list'), self.dated(self.FRIDAY, teacher=self.teacher))
        second = self.client.post(reverse('teaching-slot-list'), self.dated(self.FRIDAY, teacher=self.other_teacher))

        self.assertEqual((first.status_code, second.status_code), (201, 201))

    def test_clearing_the_date_turns_a_dated_lesson_back_into_a_weekly_one(self):
        created = self.client.post(reverse('teaching-slot-list'), self.dated(self.FRIDAY)).data

        response = self.client.patch(reverse('teaching-slot-detail', args=[created['id']]), {'date': None})

        self.assertEqual(response.status_code, 200)
        slot = TeachingSlot.objects.get()
        self.assertIsNone(slot.date)
        self.assertFalse(slot.is_one_off)

    def test_editing_a_period_keeps_its_own_time(self):
        """The clash check has to ignore the row being edited, or no period that
        keeps its time could ever be saved twice."""
        created = self.client.post(reverse('teaching-slot-list'), self.weekly()).data

        response = self.client.patch(reverse('teaching-slot-detail', args=[created['id']]), {'room': '202'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(TeachingSlot.objects.get().room, '202')

    def test_listing_one_date_gives_that_day_dated_lessons_only(self):
        self.client.post(reverse('teaching-slot-list'), self.weekly(start='09:45'))
        one_off = self.client.post(
            reverse('teaching-slot-list'), self.dated(self.FRIDAY, start='14:00', end_time='15:00')
        ).data['id']

        response = self.client.get(reverse('teaching-slot-list'), {'date': self.FRIDAY})

        self.assertEqual([s['id'] for s in response.data['results']], [one_off])

    def test_listing_one_date_can_include_the_weekly_periods_that_fall_on_it(self):
        weekly = self.client.post(reverse('teaching-slot-list'), self.weekly(start='09:45')).data['id']
        one_off = self.client.post(
            reverse('teaching-slot-list'), self.dated(self.FRIDAY, start='14:00', end_time='15:00')
        ).data['id']

        response = self.client.get(reverse('teaching-slot-list'), {'date': self.FRIDAY, 'include_weekly': 'true'})

        self.assertEqual(sorted(s['id'] for s in response.data['results']), sorted([weekly, one_off]))
        # Ordered by the time the day runs, earliest first.
        self.assertEqual([s['id'] for s in response.data['results']], [weekly, one_off])

    def test_listing_one_date_leaves_out_periods_from_another_weekday(self):
        """A Monday period must not turn up in the Friday list."""
        self.client.post(reverse('teaching-slot-list'), self.weekly(day=0, start='09:45'))

        response = self.client.get(reverse('teaching-slot-list'), {'date': self.FRIDAY, 'include_weekly': 'true'})

        self.assertEqual(response.data['count'], 0)

    def test_the_whole_list_still_shows_every_period(self):
        self.client.post(reverse('teaching-slot-list'), self.weekly())
        self.client.post(reverse('teaching-slot-list'), self.dated(self.FRIDAY, start='14:00', end_time='15:00'))

        response = self.client.get(reverse('teaching-slot-list'))

        self.assertEqual(response.data['count'], 2)

    def test_a_teacher_only_sees_their_own_periods(self):
        mine = self.client.post(reverse('teaching-slot-list'), self.dated(self.FRIDAY)).data['id']
        self.client.post(reverse('teaching-slot-list'), self.dated(self.FRIDAY, teacher=self.other_teacher, start='14:00'))
        self.client.force_authenticate(self.teacher)

        response = self.client.get(reverse('teaching-slot-list'))

        self.assertEqual([s['id'] for s in response.data['results']], [mine])

    def test_a_teacher_cannot_add_a_period(self):
        self.client.force_authenticate(self.teacher)

        response = self.client.post(reverse('teaching-slot-list'), self.dated(self.FRIDAY))

        self.assertEqual(response.status_code, 403)

    def test_the_weekday_filter_still_reports_a_mismatch(self):
        response = self.client.post(reverse('teaching-slot-list'), self.weekly(start='12:00', end_time='11:00'))

        self.assertEqual(response.status_code, 400)
