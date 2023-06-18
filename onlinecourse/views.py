from django.shortcuts import render
from django.http import HttpResponseRedirect
# <HINT> Import any new Models here
from .models import Course, Enrollment
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login, logout, authenticate
import logging
# Get an instance of a logger
logger = logging.getLogger(__name__)
# Create your views here.


def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
    elif request.method == 'POST':
        # Check if user exists
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']
        user_exist = False
        try:
            User.objects.get(username=username)
            user_exist = True
        except:
            logger.error("New user")
        if not user_exist:
            user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name,
                                            password=password)
            login(request, user)
            return redirect("onlinecourse:index")
        else:
            context['message'] = "User already exists."
            return render(request, 'onlinecourse/user_registration_bootstrap.html', context)


def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        else:
            context['message'] = "Invalid username or password."
            return render(request, 'onlinecourse/user_login_bootstrap.html', context)
    else:
        return render(request, 'onlinecourse/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


def check_if_enrolled(user, course):
    is_enrolled = False
    if user.id is not None:
        # Check if user enrolled
        num_results = Enrollment.objects.filter(user=user, course=course).count()
        if num_results > 0:
            is_enrolled = True
    return is_enrolled


# CourseListView
class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            if user.is_authenticated:
                course.is_enrolled = check_if_enrolled(user, course)
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_detail_bootstrap.html'


def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    is_enrolled = check_if_enrolled(user, course)
    if not is_enrolled and user.is_authenticated:
        # Create an enrollment
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(reverse(viewname='onlinecourse:course_details', args=(course.id,)))


         # <HINT> Create a submit view to create an exam submission record for a course enrollment,
         # you may implement it based on following logic:
         # Get user and course object, then get the associated enrollment object created when the user enrolled the course
         # Create a submission object referring to the enrollment
         # Collect the selected choices from exam form
         # Add each selected choice object to the submission object
         # Redirect to show_exam_result with the submission id
#def submit(request, course_id):
def submit(request, course_id):

    # Get the current user and course object
    user = request.user
    course = get_object_or_404(Course, pk=course_id)

    # Get the associated enrollment object
    enrollment = Enrollment.objects.get(user=user, course=course)

    # Create a new submission object referring to the enrollment
    submission = Submission.objects.create(enrollment=enrollment)

    # Collect the selected choices from HTTP request object
    submitted_answers = extract_answers(request)

    # Add each selected choice object to the submission object
    for choice_id in submitted_answers:
        choice = get_object_or_404(Choice, pk=choice_id)
        submission.choices.add(choice)

    # Redirect to a show_exam_result view with the submission id
    return HttpResponseRedirect(reverse('onlinecourse:show_exam_result', args=(course.id, submission.id,)))


    # <HINT> A example method to collect the selected choices from the exam form from the request object
    def extract_answers(request):
    submitted_answers = []
    for key in request.POST:
        if key.startswith('choice'):
            value = request.POST.getlist(key)
            submitted_answers.extend([int(v) for v in value])
    return submitted_answers


       # <HINT> Create an exam result view to check if learner passed exam and show their question results and result for each question,
       # you may implement it based on the following logic:
        # Get course and submission based on their ids
        # Get the selected choice ids from the submission record
        # For each selected choice, check if it is a correct answer or not
        # Calculate the total score
    def show_exam_result(request, course_id, submission_id):
    # Get the course and submission objects based on their ids
    course = get_object_or_404(Course, pk=course_id)
    submission = get_object_or_404(Submission, pk=submission_id)

    # Get the selected choice ids from the submission record
    selected_ids = submission.choices.values_list('id', flat=True)

    # Initialize the total score
    total_score = 0

    # Initialize the exam results
    # Initialize the exam results
    exam_results = {}

    # For each question, check if it gets score
    for question in course.question_set.all():
        if question.is_get_score(selected_ids):
            total_score += question.grade

        # Get all choices for this question
        all_choices = question.choice_set.all()

        # Get the selected choices for this question
        selected_choices = question.choice_set.filter(id__in=selected_ids)

        # Append each choice to the exam results
        question_choices = []
        for choice in all_choices:
            is_correct = choice.is_correct
            was_selected = choice in selected_choices
            question_choices.append((choice.choice_text, is_correct, was_selected))

        exam_results[question.question_text] = question_choices

    # Calculate the grade
    grade = (total_score / course.question_set.aggregate(total_grade=Sum('grade'))['total_grade']) * 100

    # Add the course, total_score, grade, and exam_results to context for rendering HTML page
    context = {
        'course': course,
        'total_score': total_score,
        'grade': grade,
        'exam_results': exam_results,
    }

    return render(request, 'onlinecourse/exam_result_bootstrap.html', context)
